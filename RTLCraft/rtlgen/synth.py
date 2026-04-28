"""
rtlgen.synth — ABC-based logic synthesis, optimization, and technology mapping.

Flow:
    RTL IR (via BLIF) → ABC read_blif → strash (AIG) → resyn2 →
    read_lib tech.lib → map → write_verilog mapped.v
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SynthResult:
    """综合结果容器。"""

    area: float
    delay: float
    gates: int
    depth: int
    stdout: str
    stderr: str
    mapped_verilog: Optional[str] = None


class WireLoadModel:
    """简单的 Wire Load Model，用于后映射的互连线延迟估算。

    公式：wire_delay = fanout * slope + intercept
    """

    def __init__(self, name: str = "wlm_default", slope: float = 0.05, intercept: float = 0.01):
        self.name = name
        self.slope = slope  # ns per fanout
        self.intercept = intercept  # ns base

    def estimate_delay(self, fanout: int) -> float:
        return fanout * self.slope + self.intercept

    def report(self) -> str:
        return f"WireLoadModel({self.name}, slope={self.slope}ns/fanout, intercept={self.intercept}ns)"


class ABCSynthesizer:
    """调用 Berkeley ABC 进行逻辑综合与工艺映射。"""

    def __init__(self, abc_path: Optional[str] = None):
        self.abc_path = abc_path or self._find_abc()

    @staticmethod
    def _find_abc() -> Optional[str]:
        return shutil.which("abc")

    def is_available(self) -> bool:
        return self.abc_path is not None and os.path.exists(self.abc_path)

    def generate_abc_script(
        self,
        input_blif: str,
        liberty: Optional[str],
        output_verilog: str,
        output_aig: Optional[str] = None,
        output_blif: Optional[str] = None,
        optimization: str = "resyn2",
        wlm: Optional[WireLoadModel] = None,
        upsize: bool = False,
        dnsize: bool = False,
    ) -> str:
        """生成 ABC 命令脚本。"""
        lines: List[str] = []
        lines.append(f'read_blif "{input_blif}"')
        lines.append("strash")
        if optimization:
            if optimization == "resyn2":
                # Expand the resyn2 alias so ABC does not need abc.rc
                lines.append("balance; rewrite; refactor; balance; rewrite; rewrite -z; balance; refactor -z; rewrite -z; balance")
            else:
                lines.append(optimization)
        if liberty and os.path.exists(liberty):
            lines.append(f'read_lib "{liberty}"')
            if wlm is not None:
                lines.append(f"# {wlm.report()}")
            lines.append("map")
            if upsize:
                lines.append("upsize")
            if dnsize:
                lines.append("dnsize")
            lines.append("topo")
            lines.append("print_stats")
        if output_aig:
            lines.append(f'write_aiger -z "{output_aig}"')
        if output_blif:
            # use -j to emit .names gates (avoids empty combinational logic in some ABC builds)
            lines.append(f'write_blif -j "{output_blif}"')
        lines.append(f'write_verilog "{output_verilog}"')
        lines.append("quit")
        return "\n".join(lines)

    def write_run_script(self, script_path: str, **kwargs) -> str:
        """生成独立的 ABC 运行脚本（shell + abc cmd），方便用户手动执行。"""
        abc_cmds = self.generate_abc_script(**kwargs)
        cmd_file = kwargs["input_blif"] + ".abc"
        with open(cmd_file, "w") as f:
            f.write(abc_cmds + "\n")

        sh = f"""#!/bin/bash
# Auto-generated ABC synthesis script
set -e
ABC="{self.abc_path or 'abc'}"
if ! command -v "$ABC" &> /dev/null; then
    echo "Error: ABC not found. Please install Berkeley ABC and ensure it is in PATH."
    echo "Installation: https://github.com/berkeley-abc/abc"
    exit 1
fi
"$ABC" -f "{cmd_file}"
echo "Synthesis completed: {kwargs.get('output_verilog', 'mapped.v')}"
"""
        with open(script_path, "w") as f:
            f.write(sh)
        os.chmod(script_path, 0o755)
        return script_path

    def run(
        self,
        input_blif: str,
        liberty: Optional[str] = None,
        output_verilog: str = "mapped.v",
        output_aig: Optional[str] = None,
        output_blif: Optional[str] = None,
        optimization: str = "resyn2",
        wlm: Optional[WireLoadModel] = None,
        upsize: bool = False,
        dnsize: bool = False,
        cwd: Optional[str] = None,
    ) -> SynthResult:
        """执行 ABC 综合流程。"""
        if not self.is_available():
            script_path = (cwd or ".") + "/run_abc.sh"
            self.write_run_script(
                script_path=script_path,
                input_blif=input_blif,
                liberty=liberty or "",
                output_verilog=output_verilog,
                output_aig=output_aig,
                output_blif=output_blif,
                optimization=optimization,
                wlm=wlm,
                upsize=upsize,
                dnsize=dnsize,
            )
            raise RuntimeError(
                f"ABC executable not found. A run script has been generated at {script_path}. "
                f"Please install ABC (https://github.com/berkeley-abc/abc) and rerun."
            )

        abc_cmds = self.generate_abc_script(
            input_blif=input_blif,
            liberty=liberty,
            output_verilog=output_verilog,
            output_aig=output_aig,
            output_blif=output_blif,
            optimization=optimization,
            wlm=wlm,
            upsize=upsize,
            dnsize=dnsize,
        )
        cmd_file = input_blif + ".abc"
        with open(cmd_file, "w") as f:
            f.write(abc_cmds + "\n")

        proc = subprocess.run(
            [self.abc_path, "-f", cmd_file],
            capture_output=True,
            text=True,
            cwd=cwd,
        )

        area, delay, gates, depth = 0.0, 0.0, 0, 0
        mapped_verilog = None

        if os.path.exists(output_verilog):
            with open(output_verilog, "r") as f:
                mapped_verilog = f.read()

        import re
        for line in proc.stdout.splitlines():
            if "area" in line and "delay" in line and "nd =" in line:
                m = re.search(r"area\s*=\s*([\d.]+)", line)
                if m:
                    try:
                        area = float(m.group(1))
                    except ValueError:
                        pass
                m = re.search(r"delay\s*=\s*(-?[\d.]+)", line)
                if m:
                    try:
                        delay = float(m.group(1))
                    except ValueError:
                        pass
                m = re.search(r"nd\s*=\s*(\d+)", line)
                if m:
                    try:
                        gates = int(m.group(1))
                    except ValueError:
                        pass
                m = re.search(r"lev\s*=\s*(\d+)", line)
                if m:
                    try:
                        depth = int(m.group(1))
                    except ValueError:
                        pass

        return SynthResult(
            area=area,
            delay=delay,
            gates=gates,
            depth=depth,
            stdout=proc.stdout,
            stderr=proc.stderr,
            mapped_verilog=mapped_verilog,
        )
