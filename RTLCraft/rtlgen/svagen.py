"""
rtlgen.svagen — SystemVerilog Assertion (SVA) 生成器

基于 pyRTL Module 的端口自动推断并生成常用形式验证属性，
支持 handshake (valid/ready/data) 检查、复位检查以及用户自定义断言。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from rtlgen.core import Module, Input


class SVAEmitter:
    """SVA 代码发射器。"""

    def __init__(self, indent: str = "    "):
        self.indent = indent

    def emit_assertions(
        self,
        module: Module,
        assertion_name: Optional[str] = None,
        custom_assertions: Optional[List[Tuple[str, str]]] = None,
        generate_bind: bool = True,
    ) -> str:
        """生成 SVA 断言模块及可选的 bind 语句。

        参数:
            module: 目标 DUT 模块
            assertion_name: 断言模块名（默认 {module.name}_assertions）
            custom_assertions: 用户自定义断言列表 [(name, expr_str), ...]
            generate_bind: 是否同时生成 bind 语句
        """
        base = assertion_name or f"{module.name}_assertions"
        clk = self._find_clock(module) or "clk"
        rst = self._find_reset(module)

        ports = []
        for n, s in module._inputs.items():
            sv_w = self._to_sv_width(s.width)
            ports.append(f"    input {sv_w}{n}")
        for n, s in module._outputs.items():
            sv_w = self._to_sv_width(s.width)
            ports.append(f"    input {sv_w}{n}")
        port_str = ",\n".join(ports)

        lines: List[str] = []

        if generate_bind:
            lines.append(f"bind {module.name} {base} u_{base} (.*);")
            lines.append("")

        lines.append(f"module {base} (")
        lines.append(port_str)
        lines.append(");")
        lines.append("")

        idx = 0

        # Reset assertion
        if rst:
            lines.append(f"    // Reset assertion")
            if rst.endswith("_n") or rst.endswith("N"):
                lines.append(
                    f'    property p_reset_release;\n'
                    f'        @(posedge {clk}) $fell({rst}) |=> ##[1:10] {rst};\n'
                    f'    endproperty\n'
                    f'    ap_reset_release: assert property(p_reset_release);'
                )
            else:
                lines.append(
                    f'    property p_reset_release;\n'
                    f'        @(posedge {clk}) $rose({rst}) |=> ##[1:10] !{rst};\n'
                    f'    endproperty\n'
                    f'    ap_reset_release: assert property(p_reset_release);'
                )
            lines.append("")

        # Handshake assertions
        hs = self._detect_handshake(module)
        if hs:
            valid, ready, data = hs
            lines.append(f"    // Handshake assertions")
            lines.append(
                f'    property p_valid_data_stable;\n'
                f'        @(posedge {clk}) {self._disable_iff(rst)}\n'
                f'        ({valid} && !{ready}) |=> $stable({data});\n'
                f'    endproperty\n'
                f'    ap_valid_data_stable: assert property(p_valid_data_stable);'
            )
            lines.append(
                f'    property p_valid_until_ready;\n'
                f'        @(posedge {clk}) {self._disable_iff(rst)}\n'
                f'        {valid} && !{ready} |=> {valid};\n'
                f'    endproperty\n'
                f'    ap_valid_until_ready: assert property(p_valid_until_ready);'
            )
            lines.append("")

        # Custom assertions
        if custom_assertions:
            lines.append("    // Custom assertions")
            for name, expr in custom_assertions:
                lines.append(
                    f'    property p_{name};\n'
                    f'        @(posedge {clk}) {self._disable_iff(rst)}\n'
                    f'        {expr};\n'
                    f'    endproperty\n'
                    f'    ap_{name}: assert property(p_{name});'
                )
            lines.append("")

        lines.append(f"endmodule : {base}")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _to_sv_width(width: int) -> str:
        return f"[{width - 1}:0] " if width > 1 else ""

    def _find_clock(self, module: Module) -> Optional[str]:
        for n in ["clk", "clock", "aclk", "pclk"]:
            if n in module._inputs:
                return n
        return None

    def _find_reset(self, module: Module) -> Optional[str]:
        for n in ["rst_n", "reset_n", "aresetn", "rst", "reset", "areset"]:
            if n in module._inputs:
                return n
        return None

    def _disable_iff(self, rst: Optional[str]) -> str:
        if not rst:
            return ""
        if rst.endswith("_n") or rst.endswith("N"):
            return f"disable iff (!{rst})"
        return f"disable iff ({rst})"

    def _detect_handshake(self, module: Module) -> Optional[Tuple[str, str, str]]:
        """自动检测 valid/ready/data 握手组。"""
        inputs = set(module._inputs.keys())
        outputs = set(module._outputs.keys())
        all_ports = inputs | outputs

        candidates = []
        for prefix in ["", "in_", "out_", "s_", "m_"]:
            valid = f"{prefix}valid"
            ready = f"{prefix}ready"
            if valid in all_ports and ready in all_ports:
                data = f"{prefix}data"
                if data in all_ports:
                    candidates.append((valid, ready, data))

        # 优先返回无前缀的
        for c in candidates:
            if c[0] == "valid":
                return c
        return candidates[0] if candidates else None
