"""EpisodicMemory — cross-session memory for agent learning.

Persists key events (decisions, errors, successes) from each session
and surfaces relevant past experiences at the start of future sessions.

Storage:
  .rtlcraft/memory/
    sessions/<ts>_<sid>.jsonl
    patterns/errors.json
    patterns/successes.json
    index.json
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


class EpisodicMemory:
    """Cross-session episodic memory for the agent.

    Usage:
        mem = EpisodicMemory("/path/to/project")
        mem.record("error", 3, "File write failed", ...)
        mem.save_session(summary="Generated riscv64_soc")
        patterns = mem.get_error_patterns()
    """

    def __init__(self, base_dir: str, session_id: Optional[str] = None):
        self._mem_dir = os.path.join(base_dir, ".rtlcraft", "memory")
        self._sessions_dir = os.path.join(self._mem_dir, "sessions")
        self._patterns_dir = os.path.join(self._mem_dir, "patterns")
        self._session_id = session_id or uuid.uuid4().hex[:12]

        os.makedirs(self._sessions_dir, exist_ok=True)
        os.makedirs(self._patterns_dir, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        self._session_file = os.path.join(
            self._sessions_dir, f"{ts}_{self._session_id}.jsonl"
        )
        self._episodes: List[Dict[str, Any]] = []
        self._error_patterns: List[Dict[str, Any]] = self._load_patterns("errors")
        self._success_patterns: List[Dict[str, Any]] = self._load_patterns("successes")

    # ── public API ──

    def record(
        self,
        episode_type: str,
        layer: int,
        task: str,
        context: str,
        action: str,
        result: str,
        patterns: Optional[List[str]] = None,
    ) -> None:
        """Record a single episode. Written to JSONL immediately (crash-safe)."""
        episode = {
            "session_id": self._session_id,
            "timestamp": time.time(),
            "type": episode_type,
            "layer": layer,
            "task": task[:200],
            "context": context[:500],
            "action": action[:500],
            "result": result[:500],
            "patterns": patterns or [],
        }
        self._episodes.append(episode)
        try:
            with open(self._session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(episode, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def save_session(self, summary: str) -> None:
        """Finalize session: aggregate episodes into patterns."""
        if not self._episodes:
            return

        session_summary = {
            "session_id": self._session_id,
            "timestamp": time.time(),
            "summary": summary,
            "episode_count": len(self._episodes),
            "errors": sum(1 for e in self._episodes if e["type"] == "error"),
            "successes": sum(1 for e in self._episodes if e["type"] == "success"),
            "layers": sorted({e["layer"] for e in self._episodes}),
        }

        for ep in self._episodes:
            if ep["type"] == "error" and ep["patterns"]:
                self._merge_pattern("errors", ep)
            elif ep["type"] == "success" and ep["patterns"]:
                self._merge_pattern("successes", ep)

        index_path = os.path.join(self._mem_dir, "index.json")
        index: List[Dict[str, Any]] = []
        if os.path.exists(index_path):
            try:
                with open(index_path, "r") as f:
                    index = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        index.append(session_summary)
        index = index[-100:]
        try:
            with open(index_path, "w") as f:
                json.dump(index, f, indent=2)
        except OSError:
            pass

    def load_relevant(self, context: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Find past episodes relevant to the current context."""
        if not context:
            return self._error_patterns[:top_k]
        query_tokens = _tokenize(context)

        scored: List[tuple[float, Dict[str, Any]]] = []
        for ep in self._episodes:
            text = " ".join(str(ep.get(k, "")) for k in ("task", "context", "action", "result"))
            overlap = len(query_tokens & _tokenize(text))
            if overlap > 0:
                scored.append((overlap, ep))

        for pat in self._error_patterns:
            text = " ".join(str(pat.get(k, "")) for k in ("pattern", "context", "solution"))
            overlap = len(query_tokens & _tokenize(text))
            if overlap > 0:
                scored.append((overlap * 1.5, {"type": "error_pattern", **pat}))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]

    def get_error_patterns(self) -> List[Dict[str, Any]]:
        return self._error_patterns

    def get_success_patterns(self) -> List[Dict[str, Any]]:
        return self._success_patterns

    def format_for_prompt(self) -> str:
        """Format past experiences as a system prompt section."""
        parts = []
        if self._error_patterns:
            parts.append("## Past Lessons (avoid these)")
            for p in self._error_patterns[-3:]:
                parts.append(f"- {p.get('pattern', '?')}: {p.get('solution', '')[:200]}")
        if self._success_patterns:
            parts.append("\n## Past Success Patterns")
            for p in self._success_patterns[-3:]:
                parts.append(f"- {p.get('pattern', '?')}: {p.get('context', '')[:200]}")
        return "\n".join(parts)

    @property
    def episode_count(self) -> int:
        return len(self._episodes)

    # ── internal ──

    def _merge_pattern(self, pattern_type: str, episode: Dict[str, Any]) -> None:
        patterns_path = os.path.join(self._patterns_dir, f"{pattern_type}.json")
        existing: List[Dict[str, Any]] = []
        if os.path.exists(patterns_path):
            try:
                with open(patterns_path, "r") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        for pat_name in episode.get("patterns", []):
            found = False
            for ep in existing:
                if ep.get("pattern") == pat_name:
                    ep["last_seen"] = time.time()
                    ep["count"] = ep.get("count", 0) + 1
                    ep["context"] = episode.get("context", "")
                    if pattern_type == "errors":
                        ep["solution"] = episode.get("result", "")
                    found = True
                    break
            if not found:
                entry: Dict[str, Any] = {
                    "pattern": pat_name,
                    "type": pattern_type,
                    "first_seen": time.time(),
                    "last_seen": time.time(),
                    "count": 1,
                    "context": episode.get("context", ""),
                }
                if pattern_type == "errors":
                    entry["solution"] = episode.get("result", "")
                existing.append(entry)

        existing.sort(key=lambda x: x.get("count", 0), reverse=True)
        existing = existing[:50]
        try:
            with open(patterns_path, "w") as f:
                json.dump(existing, f, indent=2)
        except OSError:
            pass
        if pattern_type == "errors":
            self._error_patterns = existing
        else:
            self._success_patterns = existing

    def _load_patterns(self, pattern_type: str) -> List[Dict[str, Any]]:
        path = os.path.join(self._patterns_dir, f"{pattern_type}.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []


def _tokenize(text: str) -> Set[str]:
    """Simple lowercase tokenization with Chinese support."""
    tokens = re.findall(r"[a-z0-9_\u4e00-\u9fff]+", text.lower())
    stop_words = {
        "the", "a", "an", "is", "was", "to", "of", "in", "for",
        "on", "and", "or", "with", "this", "that", "it", "at",
        "by", "from", "as", "be", "are", "were", "been",
    }
    return {t for t in tokens if len(t) > 2 and t not in stop_words}
