"""
Tool Adapter Base — abstract interface for all EDA tool adapters.

Each adapter encapsulates:
1. Environment setup (source bash, set paths)
2. Tcl script generation from design state
3. Tool invocation (subprocess)
4. Log/report parsing back into design state
"""
from __future__ import annotations

import logging
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..db.design_state import DesignState, FlowStage, StageResult, StageStatus

logger = logging.getLogger("ic_backend")


class ToolAdapter(ABC):
    """Base class for EDA tool adapters."""

    tool_name: str = "unknown"
    stage: FlowStage = FlowStage.INIT
    env_script: str = ""
    tool_family: str = ""  # bash script to source for tool environment
    tcl_flag: str = "-f"  # command-line flag used to pass the Tcl script

    def __init__(self, state: DesignState):
        self.state = state
        self.work_dir: Path | None = None

    @property
    def resolved_env_script(self) -> str:
        """Resolve environment script from config, fallback to class default."""
        if self.state and self.state.config:
            eda = getattr(self.state.config, "eda", None)
            if eda and self.tool_family:
                script = eda.get_script(self.tool_family)
                if script:
                    return script
        return self.env_script

    @abstractmethod
    def generate_script(self) -> str:
        """Generate the Tcl script content for this stage."""
        ...

    @abstractmethod
    def parse_results(self) -> None:
        """Parse tool output and update stage results in self.state."""
        ...

    def setup_work_dir(self, stage_name: str) -> Path:
        root = Path(self.state.work_root) / stage_name
        root.mkdir(parents=True, exist_ok=True)
        (root / "rpt").mkdir(exist_ok=True)
        (root / "out").mkdir(exist_ok=True)
        (root / "log").mkdir(exist_ok=True)
        self.work_dir = root
        return root

    def write_tcl(self, script_content: str, filename: str = "run.tcl") -> Path:
        assert self.work_dir is not None
        tcl_path = self.work_dir / filename
        tcl_path.write_text(script_content)
        return tcl_path

    def run_tool(
        self,
        shell_cmd: str,
        tcl_file: Path,
        log_file: str = "run.log",
        timeout_hours: float = 24.0,
    ) -> tuple[int, Path]:
        """Run the EDA tool via subprocess."""
        assert self.work_dir is not None
        log_path = self.work_dir / "log" / log_file

        env = self.resolved_env_script
        # Use absolute path for the Tcl file because cwd is set to work_dir.
        tcl_abs = str(Path(tcl_file).resolve())
        full_cmd = f"source {env} 2>/dev/null; {shell_cmd} {self.tcl_flag} {tcl_abs}"
        if not env:
            full_cmd = f"{shell_cmd} {self.tcl_flag} {tcl_abs}"

        logger.info(f"[{self.tool_name}] Running: {full_cmd}")
        logger.info(f"[{self.tool_name}] Work dir: {self.work_dir}")

        with open(log_path, "w") as log_f:
            log_f.write(f"# Command: {full_cmd}\n")
            log_f.write(f"# Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            proc = subprocess.Popen(
                ["bash", "-c", full_cmd],
                stdout=log_f,
                stderr=subprocess.STDOUT,
                cwd=str(self.work_dir),
                env=None,  # inherit parent env
            )

            try:
                returncode = proc.wait(timeout=int(timeout_hours * 3600))
            except subprocess.TimeoutExpired:
                proc.kill()
                returncode = -1
                logger.error(f"[{self.tool_name}] Timeout after {timeout_hours}h")

        logger.info(f"[{self.tool_name}] Exit code: {returncode}")
        return returncode, log_path

    def run_tool_batch(
        self,
        shell_cmd: str,
        tcl_file: Path,
        log_file: str = "run.log",
        timeout_hours: float = 24.0,
    ) -> tuple[int, Path]:
        """Run tool in batch mode (no GUI, exit on completion)."""
        return self.run_tool(shell_cmd, tcl_file, log_file, timeout_hours)

    def execute(self) -> StageResult:
        """Full stage execution: generate -> run -> parse -> return result."""
        result = self.state.get_stage_result(self.stage)
        result.status = StageStatus.RUNNING

        try:
            script = self.generate_script()
            tcl_path = self.write_tcl(script)
            result.log_file = str(self.work_dir / "log" / "run.log")

            returncode, log_path = self.run_tool_batch(
                self._get_shell_cmd(), tcl_path
            )

            result.elapsed_seconds = 0  # set by caller
            result.log_file = str(log_path)

            if returncode == 0:
                result.status = StageStatus.PASSED
            else:
                result.status = StageStatus.FAILED
                result.messages.append(f"Tool exited with code {returncode}")

            self.parse_results()
            result.work_dir = str(self.work_dir)

        except Exception as exc:
            result.status = StageStatus.FAILED
            result.messages.append(f"Exception: {exc}")
            logger.exception(f"[{self.tool_name}] Stage failed with exception")

        return result

    @abstractmethod
    def _get_shell_cmd(self) -> str:
        """Return the shell command to launch the tool."""
        ...
