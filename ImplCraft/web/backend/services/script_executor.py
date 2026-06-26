"""
Script Executor — preview, confirm, and execute EDA scripts.

Workflow:
1. Generate script content (Tcl/shell)
2. Store in database with 'generated' status
3. Frontend displays preview with syntax highlighting
4. User confirms execution
5. Execute in subprocess, capture output
6. Update script record with results

This ensures human-in-the-loop control over EDA tool execution.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..db.models import ScriptRecord, DesignRecord
from ..db.engine import get_session

logger = logging.getLogger("implcraft.executor")


class ScriptExecutor:
    """
    Manages script preview and execution with confirmation workflow.
    
    Usage:
        executor = ScriptExecutor()
        script_id = executor.generate_script(design_id, stage, content, "run.tcl")
        # User reviews preview in frontend
        executor.execute_script(script_id, env_script="/tools/env.sh")
    """

    def __init__(self, work_root: str | Path = "./work"):
        self.work_root = Path(work_root)
        self.work_root.mkdir(parents=True, exist_ok=True)
        self._running_processes: dict[int, subprocess.Popen] = {}

    def generate_script(
        self,
        design_id: int,
        stage_name: str,
        content: str,
        filename: str = "run.tcl",
        script_type: str = "tcl",
    ) -> int:
        """
        Generate a script and store it for preview.
        Returns the script record ID.
        """
        preview = self._generate_preview(content, script_type)

        with get_session() as session:
            record = ScriptRecord(
                design_id=design_id,
                stage_name=stage_name,
                script_type=script_type,
                filename=filename,
                content=content,
                preview_content=preview,
                status="generated",
            )
            session.add(record)
            session.flush()
            script_id = record.id

            self._write_script_file(design_id, stage_name, filename, content)

        logger.info(f"Generated script {script_id}: {filename} for design {design_id}/{stage_name}")
        return script_id

    def _write_script_file(self, design_id: int, stage_name: str,
                           filename: str, content: str) -> Path:
        """Write script content to filesystem."""
        script_dir = self.work_root / f"design_{design_id}" / stage_name / "scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        script_path = script_dir / filename
        script_path.write_text(content)
        script_path.chmod(0o755)
        return script_path

    def _generate_preview(self, content: str, script_type: str) -> str:
        """Generate a preview version with annotations."""
        lines = content.split("\n")
        preview_lines = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                preview_lines.append(f"{i:4d} | ")
                continue

            if script_type == "tcl":
                if stripped.startswith("#"):
                    preview_lines.append(f"{i:4d} | {line}  # COMMENT")
                elif stripped.startswith("proc "):
                    preview_lines.append(f"{i:4d} | {line}  # PROCEDURE")
                elif "source " in stripped:
                    preview_lines.append(f"{i:4d} | {line}  # SOURCE")
                elif "exec " in stripped or "sh " in stripped:
                    preview_lines.append(f"{i:4d} | {line}  # SHELL CMD")
                else:
                    preview_lines.append(f"{i:4d} | {line}")
            else:
                if stripped.startswith("#"):
                    preview_lines.append(f"{i:4d} | {line}  # COMMENT")
                else:
                    preview_lines.append(f"{i:4d} | {line}")

        return "\n".join(preview_lines)

    def execute_script(
        self,
        script_id: int,
        env_script: str = "",
        timeout_hours: float = 24.0,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Execute a confirmed script.
        Returns execution result with exit_code and log.
        """
        with get_session() as session:
            record = session.query(ScriptRecord).filter_by(id=script_id).first()
            if not record:
                raise ValueError(f"Script {script_id} not found")

            if record.status == "running":
                raise ValueError(f"Script {script_id} is already running")

            if dry_run:
                record.status = "dry_run"
                record.execution_log = "[DRY RUN] Script preview only, not executed."
                return {
                    "script_id": script_id,
                    "status": "dry_run",
                    "exit_code": None,
                    "log": record.execution_log,
                }

            record.status = "running"
            session.flush()

            script_path = self._write_script_file(
                record.design_id, record.stage_name,
                record.filename, record.content,
            )

            shell_cmd = self._build_shell_command(script_path, record.script_type)
            if env_script:
                shell_cmd = f"source {env_script} 2>/dev/null; {shell_cmd}"

            log_dir = self.work_root / f"design_{record.design_id}" / record.stage_name / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"exec_{script_id}.log"

            try:
                start_time = time.time()
                proc = subprocess.Popen(
                    ["bash", "-c", shell_cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=str(script_path.parent),
                )
                self._running_processes[script_id] = proc

                stdout, _ = proc.communicate(timeout=int(timeout_hours * 3600))
                elapsed = time.time() - start_time

                exit_code = proc.returncode
                log_content = stdout.decode("utf-8", errors="replace") if stdout else ""

                with open(log_path, "w") as f:
                    f.write(f"# Script: {record.filename}\n")
                    f.write(f"# Started: {datetime.now(timezone.utc).isoformat()}\n")
                    f.write(f"# Elapsed: {elapsed:.1f}s\n")
                    f.write(f"# Exit code: {exit_code}\n\n")
                    f.write(log_content)

                record.status = "completed" if exit_code == 0 else "failed"
                record.exit_code = exit_code
                record.execution_log = log_content[-10000:]  # Last 10K chars
                record.executed_at = datetime.now(timezone.utc)

                del self._running_processes[script_id]

                return {
                    "script_id": script_id,
                    "status": record.status,
                    "exit_code": exit_code,
                    "elapsed_seconds": elapsed,
                    "log_file": str(log_path),
                    "log_tail": log_content[-2000:] if log_content else "",
                }

            except subprocess.TimeoutExpired:
                proc.kill()
                record.status = "timeout"
                record.execution_log = f"Script timed out after {timeout_hours} hours"
                del self._running_processes[script_id]
                return {
                    "script_id": script_id,
                    "status": "timeout",
                    "exit_code": -1,
                    "log": record.execution_log,
                }
            except Exception as exc:
                record.status = "error"
                record.execution_log = str(exc)
                if script_id in self._running_processes:
                    del self._running_processes[script_id]
                return {
                    "script_id": script_id,
                    "status": "error",
                    "exit_code": -1,
                    "log": str(exc),
                }

    def _build_shell_command(self, script_path: Path, script_type: str) -> str:
        """Build the shell command to execute the script."""
        ext = script_path.suffix.lower()
        if ext == ".tcl":
            return f"tclsh {script_path}"
        elif ext == ".py":
            return f"python3 {script_path}"
        elif ext == ".sh":
            return f"bash {script_path}"
        else:
            return f"bash {script_path}"

    def cancel_script(self, script_id: int) -> bool:
        """Cancel a running script."""
        if script_id in self._running_processes:
            proc = self._running_processes[script_id]
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            del self._running_processes[script_id]

            with get_session() as session:
                record = session.query(ScriptRecord).filter_by(id=script_id).first()
                if record:
                    record.status = "cancelled"
                    record.execution_log += "\n[CANCELLED BY USER]"
            return True
        return False

    def get_running_scripts(self) -> list[int]:
        """Get list of currently running script IDs."""
        return list(self._running_processes.keys())
