"""CheckpointStore — snapshot/revert for agent tool execution.

Creates a lightweight checkpoint before each tool call and layer transition.
Uses git as the underlying versioning store so checkpoints are cheap,
diffable, and revertible.

Storage:
  .rtlcraft/checkpoints/
    .git/
    index.json
    ckpt_<ts>_<id>_L<layer>.json
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CheckpointEntry:
    id: str
    timestamp: float
    layer: int
    summary: str
    parent_id: Optional[str]
    session_id: str
    filename: str


class CheckpointStore:
    """Snapshot/revert mechanism for agent state.

    Usage:
        store = CheckpointStore("/path/to/project")
        ckpt = store.snapshot(layer=3, state={...}, summary="before bash")
        if failed:
            prev = store.revert(ckpt)
    """

    def __init__(self, base_dir: str, session_id: Optional[str] = None):
        self._ckpt_dir = os.path.join(base_dir, ".rtlcraft", "checkpoints")
        self._session_id = session_id or uuid.uuid4().hex[:12]
        self._parent_id: Optional[str] = None

        os.makedirs(self._ckpt_dir, exist_ok=True)
        self._init_git()
        self._entries: List[CheckpointEntry] = self._load_index()

    # ── public API ──

    def snapshot(
        self,
        layer: int,
        state: Dict[str, Any],
        summary: str = "",
    ) -> str:
        """Create a checkpoint and return its ID."""
        ts = time.time()
        ckpt_id = uuid.uuid4().hex[:12]
        filename = f"ckpt_{int(ts)}_{ckpt_id}_L{layer}.json"

        entry = CheckpointEntry(
            id=ckpt_id,
            timestamp=ts,
            layer=layer,
            summary=summary,
            parent_id=self._parent_id,
            session_id=self._session_id,
            filename=filename,
        )

        payload = asdict(entry) | {"state": _serialize(state)}
        filepath = os.path.join(self._ckpt_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

        self._git_commit(filename, f"ckpt {ckpt_id} L{layer}: {summary}")

        self._entries.append(entry)
        self._parent_id = ckpt_id
        self._save_index()

        return ckpt_id

    def revert(self, ckpt_id: str) -> Optional[Dict[str, Any]]:
        """Revert to a checkpoint, returning its state dict.

        Returns None if the checkpoint is not found.
        """
        entry = self._find_entry(ckpt_id)
        if entry is None:
            return None

        filepath = os.path.join(self._ckpt_dir, entry.filename)
        if not os.path.exists(filepath):
            payload = self._git_restore(entry.filename)
            if payload is None:
                return None
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                payload = json.load(f)

        self._git_restore_file(entry.filename)

        idx = next(
            (i for i, e in enumerate(self._entries) if e.id == ckpt_id), None
        )
        if idx is not None:
            self._entries = self._entries[: idx + 1]
            self._parent_id = ckpt_id
            self._save_index()

        return payload.get("state")

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        return [asdict(e) for e in self._entries]

    def diff(self, ckpt_a: str, ckpt_b: str) -> str:
        """Git-style diff between two checkpoint states."""
        entry_a, entry_b = self._find_entry(ckpt_a), self._find_entry(ckpt_b)
        if entry_a is None or entry_b is None:
            return "Checkpoint not found."
        path_a = os.path.join(self._ckpt_dir, entry_a.filename)
        path_b = os.path.join(self._ckpt_dir, entry_b.filename)
        try:
            result = subprocess.run(
                ["git", "diff", "--no-color", path_a, path_b],
                capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir,
            )
            return result.stdout or "(no diff)"
        except subprocess.TimeoutExpired:
            return "(diff timed out)"

    @property
    def current(self) -> Optional[str]:
        return self._parent_id

    @property
    def session_id(self) -> str:
        return self._session_id

    # ── git backend ──

    def _init_git(self) -> None:
        git_dir = os.path.join(self._ckpt_dir, ".git")
        if not os.path.exists(git_dir):
            subprocess.run(["git", "init"], capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir)
            subprocess.run(["git", "config", "user.name", "agent-os"], capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir)
            subprocess.run(["git", "config", "user.email", "agent@local"], capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir)
            readme = os.path.join(self._ckpt_dir, ".gitkeep")
            with open(readme, "w") as f:
                f.write("")
            subprocess.run(["git", "add", ".gitkeep"], capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir)
            subprocess.run(["git", "commit", "-m", "init"], capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir)

    def _git_commit(self, filename: str, message: str) -> None:
        subprocess.run(["git", "add", filename], capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir)
        subprocess.run(["git", "commit", "--allow-empty", "-m", message[:200]], capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir)

    def _git_restore(self, filename: str) -> Optional[Dict[str, Any]]:
        try:
            result = subprocess.run(
                ["git", "show", f"HEAD:{filename}"],
                capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except (json.JSONDecodeError, subprocess.TimeoutExpired):
            pass
        return None

    def _git_restore_file(self, filename: str) -> None:
        subprocess.run(["git", "checkout", "--", filename], capture_output=True, text=True, timeout=10, cwd=self._ckpt_dir)

    # ── index ──

    def _load_index(self) -> List[CheckpointEntry]:
        path = os.path.join(self._ckpt_dir, "index.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r") as f:
                data = json.load(f)
            entries = [CheckpointEntry(**e) for e in data]
            if entries:
                self._parent_id = entries[-1].id
            return entries
        except (json.JSONDecodeError, TypeError, KeyError):
            return []

    def _save_index(self) -> None:
        path = os.path.join(self._ckpt_dir, "index.json")
        data = [asdict(e) for e in self._entries]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._git_commit("index.json", "update index")

    def _find_entry(self, ckpt_id: str) -> Optional[CheckpointEntry]:
        for e in self._entries:
            if e.id == ckpt_id:
                return e
        return None


def _serialize(obj: Any) -> Any:
    """Recursively convert non-serializable objects to strings."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)
