"""
rtlgen.dsl.lint — Verilog Linter & Auto-Fixer

针对 rtlgen.dsl.codegen 生成的 Verilog 进行后处理验证与自动修复。
支持规则：
    - implicit_wire             : 隐式 wire 检测并补声明
    - multi_driven              : 多重驱动检测
    - unused_signal             : 未使用信号检测
    - blocking_in_seq           : 时序逻辑中阻塞赋值检测
    - latch_risk                : 组合逻辑 latch 风险检测
    - width_mismatch            : 赋值位宽不匹配检测（启发式）
    - default_nettype           : 检查/添加 `default_nettype none
    - unregistered_output       : 输出端口仅被组合逻辑驱动
    - valid_ready_protocol      : valid/ready 握手协议违例
    - constant_width_consistency: case 标签位宽与选择器不一致
    - narrow_const_comparison   : 1 位信号与 1'd1 冗余比较
    - incomplete_if_else_chain  : } else begin { if ... } 应展平
    - style_mux_chain           : 级联三元运算符建议用 case
    - style_nested_if           : 深层 if-else 嵌套 (>4 级)
    - signed_mix                : 有符号与无符号信号混合运算检测
    - signed_shift              : signed/unsigned 右移意图不清晰
    - signed_multiply           : signed/unsigned 乘法意图不清晰
    - signed_compare            : signed/unsigned 比较意图不清晰
    - hardware_division         : 检测非2的幂次硬件除法器（变量除法 / %）
    - hardware_multiplier       : 检测硬件乘法器 *
    - combinational_depth       : 估算组合逻辑算术链深度
    - no_clock                  : 时序逻辑模块缺少时钟/复位端口
    - missing_stream_protocol   : 流水线/流式模块缺少 valid_in/valid_out
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional


@dataclass
class LintIssue:
    rule: str
    line: int
    message: str
    severity: str = "warning"  # warning | error
    fix: Optional[str] = None


@dataclass
class LintResult:
    issues: List[LintIssue] = field(default_factory=list)
    fixed_text: Optional[str] = None


class VerilogLinter:
    """基于正则/行解析的轻量 Verilog Linter。"""

    def __init__(
        self,
        rules: Optional[List[str]] = None,
        auto_fix: bool = False,
    ):
        self.rules = set(rules or [
            "default_nettype",
            "implicit_wire",
            "multi_driven",
            "unused_signal",
            "blocking_in_seq",
            "latch_risk",
            "width_mismatch",
            "unregistered_output",
            "valid_ready_protocol",
            "constant_width_consistency",
            "narrow_const_comparison",
            "incomplete_if_else_chain",
            "style_mux_chain",
            "style_nested_if",
            "signed_mix",
            "signed_shift",
            "signed_multiply",
            "signed_compare",
            "hardware_division",
            "hardware_multiplier",
            "combinational_depth",
            "no_clock",
            "missing_stream_protocol",
        ])
        self.auto_fix = auto_fix

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def lint(self, text: str) -> LintResult:
        """对 Verilog 文本进行 lint，返回问题列表（并在 auto_fix=True 时返回修复后文本）。"""
        lines = text.splitlines()
        issues: List[LintIssue] = []

        # 先解析模块结构
        modules = self._parse_modules(lines)

        if "default_nettype" in self.rules:
            issues.extend(self._check_default_nettype(lines))

        for mod_name, mod_info in modules.items():
            if "implicit_wire" in self.rules:
                issues.extend(self._check_implicit_wires(mod_info, lines))
            if "multi_driven" in self.rules:
                issues.extend(self._check_multi_driven(mod_info, lines))
            if "unused_signal" in self.rules:
                issues.extend(self._check_unused_signals(mod_info, lines))
            if "blocking_in_seq" in self.rules:
                issues.extend(self._check_blocking_in_seq(mod_info, lines))
            if "latch_risk" in self.rules:
                issues.extend(self._check_latch_risk(mod_info, lines))
            if "width_mismatch" in self.rules:
                issues.extend(self._check_width_mismatch(mod_info, lines))
            if "unregistered_output" in self.rules:
                issues.extend(self._check_unregistered_output(mod_info, lines))
            if "valid_ready_protocol" in self.rules:
                issues.extend(self._check_valid_ready_protocol(mod_info, lines))
            if "constant_width_consistency" in self.rules:
                issues.extend(self._check_constant_width_consistency(mod_info, lines))
            if "narrow_const_comparison" in self.rules:
                issues.extend(self._check_narrow_const_comparison(mod_info, lines))
            if "incomplete_if_else_chain" in self.rules:
                issues.extend(self._check_incomplete_if_else_chain(mod_info, lines))
            if "style_mux_chain" in self.rules:
                issues.extend(self._check_style_mux_chain(mod_info, lines))
            if "style_nested_if" in self.rules:
                issues.extend(self._check_style_nested_if(mod_info, lines))
            if "signed_shift" in self.rules:
                issues.extend(self._check_signed_shift(mod_info, lines))
            if "signed_multiply" in self.rules:
                issues.extend(self._check_signed_binary_op_mix(
                    mod_info,
                    lines,
                    ops={"*"},
                    rule="signed_multiply",
                    summary="multiply",
                    guidance="Wrap both operands with $signed(...) or $unsigned(...) to make multiply intent explicit.",
                ))
            if "signed_compare" in self.rules:
                issues.extend(self._check_signed_binary_op_mix(
                    mod_info,
                    lines,
                    ops={"<", "<=", ">", ">=", "==", "!="},
                    rule="signed_compare",
                    summary="compare",
                    guidance="Cast both sides with $signed(...) or $unsigned(...) before comparing to make the intent explicit.",
                ))
            if "signed_mix" in self.rules:
                issues.extend(self._check_signed_mix(mod_info, lines))
            if "hardware_division" in self.rules:
                issues.extend(self._check_hardware_division(mod_info, lines))
            if "hardware_multiplier" in self.rules:
                issues.extend(self._check_hardware_multiplier(mod_info, lines))
            if "combinational_depth" in self.rules:
                issues.extend(self._check_combinational_depth(mod_info, lines))
            if "no_clock" in self.rules:
                issues.extend(self._check_no_clock(mod_info, lines))
            if "missing_stream_protocol" in self.rules:
                issues.extend(self._check_missing_stream_protocol(mod_info, lines))

        fixed = None
        if self.auto_fix:
            fixed = self._apply_fixes(lines, issues, modules)

        return LintResult(issues=issues, fixed_text=fixed)

    # -----------------------------------------------------------------
    # Parser helpers
    # -----------------------------------------------------------------
    @dataclass
    class _ModuleInfo:
        name: str
        start_line: int          # module 行（0-based）
        end_line: int            # endmodule 行（0-based）
        ports: Set[str] = field(default_factory=set)
        declared: Dict[str, Tuple[str, int]] = field(default_factory=dict)  # name -> (vartype, width)
        signed_declared: Set[str] = field(default_factory=set)
        assigned: Dict[str, List[Tuple[int, str]]] = field(default_factory=dict)  # name -> [(line, context),...]
        referenced: Set[str] = field(default_factory=set)
        always_blocks: List[Tuple[int, int, str, List[int]]] = field(default_factory=list)
        assigns: List[int] = field(default_factory=list)

    def _parse_modules(self, lines: List[str]) -> Dict[str, "VerilogLinter._ModuleInfo"]:
        modules: Dict[str, VerilogLinter._ModuleInfo] = {}
        i = 0
        while i < len(lines):
            m = re.match(r"^\s*module\s+(\w+)", lines[i])
            if m:
                mod_name = m.group(1)
                start = i
                depth = 1
                i += 1
                while i < len(lines) and depth > 0:
                    if re.search(r"\bmodule\b", lines[i]):
                        depth += 1
                    if re.search(r"\bendmodule\b", lines[i]):
                        depth -= 1
                    i += 1
                end = i - 1
                mod_info = self._ModuleInfo(name=mod_name, start_line=start, end_line=end)
                self._scan_module(lines[start:end+1], mod_info, start)
                modules[mod_name] = mod_info
            else:
                i += 1
        return modules

    def _scan_module(self, slice_lines: List[str], info: "VerilogLinter._ModuleInfo", offset: int):
        def _register_decl(name: str, vartype: str, width: int, raw_text: str) -> None:
            info.declared[name] = (vartype, width)
            if re.search(r"\bsigned\b", raw_text):
                info.signed_declared.add(name)

        in_always = False
        always_start = 0
        always_sens = ""
        always_body_lines: List[int] = []
        begin_depth = 0

        for idx, raw in enumerate(slice_lines):
            raw_no_comment = raw.split("//", 1)[0]
            line = raw.strip()
            line_no = offset + idx

            # 端口声明（在模块头中）
            port_re = re.compile(
                r"\b(input|output|inout)\b(?:\s+(?:reg|wire|logic))*?(?:\s+signed)?(?:\s*\[([^\]]+)\]\s*)?\s+([a-zA-Z_]\w*)"
            )
            for m in port_re.finditer(raw_no_comment):
                info.ports.add(m.group(3))
                _register_decl(m.group(3), m.group(1), self._width_from_range(m.group(2)), raw_no_comment)

            # 内部信号声明
            decl_re = re.compile(r"\b(logic|wire|reg)\b(?:\s+signed)?(?:\s*\[([^\]]+)\]\s*)?\s+([a-zA-Z_]\w*)")
            for m in decl_re.finditer(raw_no_comment):
                _register_decl(m.group(3), m.group(1), self._width_from_range(m.group(2)), raw_no_comment)

            # array 声明: logic [7:0] arr [0:15];
            arr_re = re.compile(r"\b(logic|wire|reg)\b(?:\s+signed)?(?:\s*\[([^\]]+)\]\s*)?([a-zA-Z_]\w*)\s*\[")
            for m in arr_re.finditer(raw_no_comment):
                _register_decl(m.group(3), m.group(1), self._width_from_range(m.group(2)), raw_no_comment)

            # parameter/localparam 不算信号

            # always 块边界（支持嵌套 begin/end）
            if re.search(r"\balways\s*@", raw):
                in_always = True
                always_start = line_no
                always_sens = raw.strip()
                always_body_lines = [line_no]
                begin_depth = len(re.findall(r"\bbegin\b", raw))
                continue

            if in_always:
                always_body_lines.append(line_no)
                begin_depth += len(re.findall(r"\bbegin\b", raw))
                begin_depth -= len(re.findall(r"\bend(?!\w)", raw))
                if begin_depth <= 0:
                    in_always = False
                    info.always_blocks.append((always_start, line_no, always_sens, always_body_lines))
                    always_body_lines = []
                continue

            # assign 语句（支持位切片 assign sig[idx] = ...）
            assign_m = re.match(r"\s*assign\s+(\w+)((?:\[[^\]]+\])?)\s*=?=", raw)
            if assign_m:
                sig = assign_m.group(1)
                idx = assign_m.group(2).strip() if assign_m.group(2) else ""
                # 若带位切片，记录为 sig[idx] 以避免与整向量驱动混淆
                sig_key = f"{sig}{idx}" if idx else sig
                info.assigned.setdefault(sig_key, []).append((line_no, "assign"))
                info.assigns.append(line_no)
                # 引用侧
                rhs = raw.split("=", 1)[1] if "=" in raw else ""
                info.referenced.update(self._extract_ids(rhs))
                continue

            # always 块内赋值（在 in_always 分支外已经 continue，所以这里不处理）

        # 二次扫描 always 块
        for _, _, sens, body_lines in info.always_blocks:
            is_seq = "posedge" in sens or "negedge" in sens
            for bl in body_lines:
                raw = slice_lines[bl - offset]
                # 左侧赋值
                for m in re.finditer(r"(\w+)\s*(?:\[[^\]]+\])?\s*(?:=(?!=)|<=)", raw):
                    sig = m.group(1)
                    ctx = "seq" if is_seq else "comb"
                    info.assigned.setdefault(sig, []).append((bl, ctx))
                # 引用
                info.referenced.update(self._extract_ids(raw))

        # 子模块实例端口连接也是引用（排除声明行本身）
        decl_line_prefixes = ("logic", "wire", "reg", "input", "output", "inout", "parameter", "localparam")
        for idx, raw in enumerate(slice_lines):
            stripped = raw.strip()
            if stripped.startswith(decl_line_prefixes):
                continue
            # .PORT(expr)
            for m in re.finditer(r"\.(\w+)\s*\(([^)]*)\)", raw):
                info.referenced.update(self._extract_ids(m.group(2)))
            info.referenced.update(self._extract_ids(raw))

        # 把端口本身也算引用，避免误报 unused
        info.referenced.update(info.ports)

    # -----------------------------------------------------------------
    # Rule implementations
    # -----------------------------------------------------------------
    def _check_default_nettype(self, lines: List[str]) -> List[LintIssue]:
        issues = []
        has_default = any(re.search(r"`default_nettype", l) for l in lines[:20])
        if not has_default:
            issues.append(LintIssue(
                rule="default_nettype",
                line=1,
                message="Missing `default_nettype none at top of file",
                severity="warning",
                fix="add_default_nettype",
            ))
        return issues

    # -----------------------------------------------------------------
    # Rule: missing_stream_protocol — 流水线/流式模块缺少 valid_in/valid_out
    # -----------------------------------------------------------------
    def _check_missing_stream_protocol(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检测含有时序逻辑的流水线/数据处理模块是否缺少 valid_in/valid_out。

        触发条件：
        1. 模块包含 always @(posedge ...) 时序块（说明是时序模块）
        2. 模块有 data_in / data_out 端口（说明是数据处理型，不是纯 FSM）
        3. 缺少 valid_in 或 valid_out 端口

        排除：纯 FSM 控制器（无 data_in/data_out）、纯组合模块。
        """
        issues: List[LintIssue] = []

        # 只检查时序模块
        has_seq = any(
            "posedge" in sens or "negedge" in sens
            for _, _, sens, _ in info.always_blocks
        )
        if not has_seq:
            return issues

        # 识别是否为数据处理型模块（有数据输入/输出端口）
        port_names = {p.lower() for p in info.ports}
        has_data_in = any("data_in" in p or "din" in p or "input_payload" in p for p in port_names)
        has_data_out = any("data_out" in p or "dout" in p or "output_payload" in p for p in port_names)
        has_stream_in = "valid_in" in port_names or "ready_in" in port_names
        has_stream_out = "valid_out" in port_names or "ready_out" in port_names

        # 排除纯 FSM 控制器（无数据端口，但有状态输出）
        is_data_module = has_data_in or has_data_out
        if not is_data_module:
            return issues

        # 排除存储器原语 (如 RamDP、ram_dp、Memory 等)
        if "ram" in info.name.lower() or "mem" in info.name.lower():
            return issues

        # 排除 NPU 内部模块 (Scheduler, SyncFIFO, Datapath 等使用专用控制协议)
        _npu_patterns = ["scheduler", "syncfifo", "datapath", "mvu", "mfu", "evrf", "ld_", "topsched"]
        if any(pat in info.name.lower() for pat in _npu_patterns):
            return issues

        # 排除外设协议接口 (I2C, SPI, etc.)
        if any("scl" in p or "sda" in p or "spi_" in p for p in port_names):
            return issues

        # 排除已有专用 valid 信号的模块 (如 data_in_valid, data_out_valid)
        has_data_valid = any("data_in_valid" in p or "data_out_valid" in p or "info_bit_valid" in p for p in port_names)
        if has_data_valid:
            return issues

        if not has_stream_in:
            issues.append(LintIssue(
                rule="missing_stream_protocol",
                line=info.start_line + 1,
                message=f"Module '{info.name}' is a clocked data-processing module (latency > 0) "
                        f"but has no 'valid_in' port. "
                        f"Pipeline modules MUST implement valid_in/valid_out handshake. "
                        f"Add 'input valid_in' and gate all pipeline registers with 'if (valid_in)'.",
                severity="error",
            ))
        if not has_stream_out:
            issues.append(LintIssue(
                rule="missing_stream_protocol",
                line=info.start_line + 1,
                message=f"Module '{info.name}' is a clocked data-processing module (latency > 0) "
                        f"but has no 'valid_out' port. "
                        f"Pipeline modules MUST implement valid_in/valid_out handshake. "
                        f"Add 'output valid_out' and delay valid_in by the module's latency.",
                severity="error",
            ))
        return issues
    # -----------------------------------------------------------------
    # Rule: hardware_division — 检测非2的幂次硬件除法器
    # -----------------------------------------------------------------
    def _check_hardware_division(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检测组合逻辑中的变量除法 / 和取模 % 操作。

        - % 操作符一律禁止（即使是常数取模），应改用位运算 & (N-1) 或条件回绕。
        - / 操作符仅对变量除法报错；常数除法（如 a / 3'd6）可被综合器优化。
        """
        issues: List[LintIssue] = []
        # 扫描 assign 和 always_comb 块中的表达式
        scan_ranges: List[Tuple[int, int, str]] = []
        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx]
            if re.match(r"\s*assign\s+", raw):
                scan_ranges.append((idx, idx, "assign"))
        for start, end, sens, body in info.always_blocks:
            if "posedge" not in sens and "negedge" not in sens:
                for bl in body:
                    scan_ranges.append((bl, bl, "comb"))
            else:
                # 时序逻辑中的 % 同样禁止（如指针回绕）
                for bl in body:
                    scan_ranges.append((bl, bl, "seq"))

        # 常数模式：\d+'[bdoh]\d+ 或纯数字
        const_pattern = re.compile(r"(\d+'[bdoh]\d+|\b\d+\b)")

        for s, e, ctx in scan_ranges:
            raw = lines[s]
            # 查找所有 / 和 % 操作符位置
            for m in re.finditer(r"(?<=[\s\w\]])\s*([/%])\s*(?=[\s\w$])", raw):
                op = m.group(1)
                # 提取操作符左右的操作数（粗略）
                lhs_raw = raw[:m.start()]
                rhs_raw = raw[m.end():]
                # 判断左右是否为常数
                lhs_is_const = bool(const_pattern.search(lhs_raw.strip().split()[-1])) if lhs_raw.strip() else False
                rhs_is_const = bool(const_pattern.match(rhs_raw.strip().split()[0])) if rhs_raw.strip() else False

                if op == '%':
                    # % 操作符一律禁止
                    issues.append(LintIssue(
                        rule="hardware_division",
                        line=s + 1,
                        message=f"Modulo operator '%' is prohibited. Use bitwise AND '& (N-1)' for power-of-2 modulus, "
                                f"or conditional wrap-around for non-power-of-2 modulus.",
                        severity="error",
                    ))
                    continue

                # 对于 / ：常数除法（右操作数为常数）可被综合器优化为乘法，不视为硬件除法器
                if rhs_is_const:
                    continue
                # 若左操作数为变量、或两边都是变量，则属于硬件除法器
                if not (lhs_is_const and rhs_is_const):
                    issues.append(LintIssue(
                        rule="hardware_division",
                        line=s + 1,
                        message=f"Hardware divider detected: '/' with variable operand in {ctx} logic. "
                                f"Variable division synthesizes to expensive divider. "
                                f"Consider using shift-based approximation or pre-computed LUT.",
                        severity="error",
                    ))
        return issues

    # -----------------------------------------------------------------
    # Rule: hardware_multiplier — 检测硬件乘法器
    # -----------------------------------------------------------------
    def _check_hardware_multiplier(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检测组合逻辑中的 * 乘法操作。

        小常数乘法（如 a * 3'd2）综合器可优化为移位/加法，但变量乘法
        或宽位乘法会综合为大型乘法器阵列，应告警。

        跳过名称中明确包含 multipl/dsp 的模块 — 这些是有意使用乘法器。
        """
        if re.search(r"multipl|dsp", info.name, re.IGNORECASE):
            return []

        issues: List[LintIssue] = []
        scan_ranges: List[Tuple[int, int, str]] = []
        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx]
            if re.match(r"\s*assign\s+", raw):
                scan_ranges.append((idx, idx, "assign"))
        for start, end, sens, body in info.always_blocks:
            if "posedge" not in sens and "negedge" not in sens:
                for bl in body:
                    scan_ranges.append((bl, bl, "comb"))

        const_pattern = re.compile(r"(\d+'[bdoh]\d+|\b\d+\b)")

        for s, e, ctx in scan_ranges:
            raw = lines[s]
            for m in re.finditer(r"(?<=[\s\w\]])\s*\*\s*(?=[\s\w$])", raw):
                lhs_raw = raw[:m.start()]
                rhs_raw = raw[m.end():]
                lhs_is_const = bool(const_pattern.search(lhs_raw.strip().split()[-1])) if lhs_raw.strip() else False
                rhs_is_const = bool(const_pattern.match(rhs_raw.strip().split()[0])) if rhs_raw.strip() else False
                # 若两个操作数都是小常数，不告警
                if lhs_is_const and rhs_is_const:
                    continue
                issues.append(LintIssue(
                    rule="hardware_multiplier",
                    line=s + 1,
                    message=f"Hardware multiplier detected: '*' in {ctx} logic. "
                            f"Variable multiplication synthesizes to large multiplier array. "
                            f"Consider using shift/add decomposition or DSP primitive instantiation.",
                    severity="error",
                ))
        return issues

    # -----------------------------------------------------------------
    # Rule: combinational_depth — 估算组合逻辑算术链深度
    # -----------------------------------------------------------------
    def _check_combinational_depth(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """估算 assign 和 always_comb 块中的算术操作链深度。

         heuristic: 每个 + - * / % << >> 算一个逻辑级。
        单条语句中连续出现 6+ 个算术操作符视为深度过大。
        跨语句的链式赋值通过 assign / wire-inline 追踪累积深度。
        """
        issues: List[LintIssue] = []
        MAX_SINGLE_EXPR_DEPTH = 6  # 单条表达式中操作符数量阈值
        MAX_CHAIN_DEPTH = 10       # 跨assign链深度阈值

        exprs: List[Tuple[int, str, str]] = []  # (line, expr_text, context)
        assign_rhs: Dict[str, Tuple[int, str]] = {}  # lhs_signal -> (line, rhs_expr)
        arith_ops_pattern = re.compile(r"[+\-*/%]|<<|>>")

        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx]
            # 标准 assign
            assign_m = re.match(r"\s*assign\s+(\w+)\s*=\s*(.+);", raw)
            if assign_m:
                lhs = assign_m.group(1)
                rhs = assign_m.group(2)
                exprs.append((idx, rhs, "assign"))
                assign_rhs[lhs] = (idx, rhs)
                continue
            # wire/logic 内联赋值: wire [7:0] foo = expr;
            inline_m = re.match(r"\s*(?:wire|logic|reg)\s+(?:\[[^\]]+\]\s+)?(\w+)\s*=\s*(.+);", raw)
            if inline_m:
                lhs = inline_m.group(1)
                rhs = inline_m.group(2)
                exprs.append((idx, rhs, "inline_assign"))
                assign_rhs[lhs] = (idx, rhs)

        for start, end, sens, body in info.always_blocks:
            if "posedge" in sens or "negedge" in sens:
                continue
            for bl in body:
                raw = lines[bl]
                m = re.search(r"(\w+(?:\[[^\]]+\])?)\s*(?:=(?!=)|<=)\s*(.+);", raw)
                if m:
                    exprs.append((bl, m.group(2), "always_comb"))

        # 单条表达式深度检查（只计数真正的算术逻辑: + - * / %；
        # << >> 是布线移位，权重低，不计入阈值）
        real_arith_pattern = re.compile(r"[+\-*/%]")

        def _strip_array_indices(expr: str) -> str:
            """Remove contents inside [...] so that address arithmetic
            (e.g. mem[base + offset]) is not counted as combinational depth."""
            result = []
            depth = 0
            for ch in expr:
                if ch == '[':
                    if depth == 0:
                        result.append('[]')
                    depth += 1
                elif ch == ']':
                    depth -= 1
                elif depth == 0:
                    result.append(ch)
            return ''.join(result)

        for line_idx, expr, ctx in exprs:
            stripped = _strip_array_indices(expr)
            ops = real_arith_pattern.findall(stripped)
            if len(ops) >= MAX_SINGLE_EXPR_DEPTH:
                issues.append(LintIssue(
                    rule="combinational_depth",
                    line=line_idx + 1,
                    message=f"Deep combinational expression: {len(ops)} arithmetic ops in single {ctx} statement. "
                            f"Consider pipelining or decomposing into multi-cycle operations.",
                    severity="warning",
                ))

        # 跨assign链深度追踪（带memoization）
        memo: Dict[str, int] = {}

        def _chain_depth(start_sig: str, visited: Set[str]) -> int:
            if start_sig in memo:
                return memo[start_sig]
            if start_sig in visited:
                return 0
            visited.add(start_sig)
            if start_sig not in assign_rhs:
                return 0
            _, rhs = assign_rhs[start_sig]
            stripped = _strip_array_indices(rhs)
            local_ops = len(real_arith_pattern.findall(stripped))
            ids = self._extract_ids(rhs)
            max_sub = 0
            for sig in ids:
                if sig in assign_rhs and sig != start_sig:
                    sub = _chain_depth(sig, visited.copy())
                    max_sub = max(max_sub, sub)
            total = local_ops + max_sub
            memo[start_sig] = total
            return total

        for sig in assign_rhs:
            depth = _chain_depth(sig, set())
            if depth >= MAX_CHAIN_DEPTH:
                line_idx, _ = assign_rhs[sig]
                issues.append(LintIssue(
                    rule="combinational_depth",
                    line=line_idx + 1,
                    message=f"Long combinational chain through assign statements: estimated {depth} logic levels "
                            f"leading to '{sig}'. Consider inserting pipeline registers to break the path.",
                    severity="error",
                ))

        return issues

    # -----------------------------------------------------------------
    # Rule: no_clock — 时序逻辑模块缺少时钟/复位端口
    # -----------------------------------------------------------------
    def _check_no_clock(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检测包含时序 always 块但缺少 clk / rst_n 端口的模块。

        纯组合模块（无 posedge/negedge）不检查。
        有 posedge/negedge 但无 clk / clock / rst / reset 端口则告警。
        """
        issues: List[LintIssue] = []
        has_seq = any(
            "posedge" in sens or "negedge" in sens
            for _, _, sens, _ in info.always_blocks
        )
        if not has_seq:
            return issues

        # 检查端口名 (支持 *_clk / *_rst* 模式，覆盖双端口 RAM 等)
        clock_names = {"clk", "clock", "aclk", "i_clk"}
        reset_names = {"rst_n", "rst", "reset_n", "reset", "areset_n", "i_rst_n"}
        has_clk = any(
            p.lower() in clock_names or p.lower().endswith("_clk")
            for p in info.ports
        )
        has_rst = any(
            p.lower() in reset_names or p.lower().endswith("_rst") or p.lower().endswith("_rst_n")
            for p in info.ports
        )

        if not has_clk:
            issues.append(LintIssue(
                rule="no_clock",
                line=info.start_line + 1,
                message=f"Module '{info.name}' contains sequential logic (posedge/negedge) but has no clock port. "
                        f"Expected port named clk/clock/aclk/i_clk.",
                severity="error",
            ))
        # 存储器原语通常不需要复位端口
        if not has_rst and not ("ram" in info.name.lower() or "mem" in info.name.lower()):
            issues.append(LintIssue(
                rule="no_clock",
                line=info.start_line + 1,
                message=f"Module '{info.name}' contains sequential logic but has no reset port. "
                        f"Expected port named rst_n/rst/reset_n/reset/areset_n/i_rst_n.",
                severity="warning",
            ))
        return issues

    def _check_implicit_wires(self, info: "VerilogLinter._ModuleInfo", lines: List[str]) -> List[LintIssue]:
        issues = []
        known = set(info.ports) | set(info.declared.keys())
        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx]
            # 只在 assign 和子模块实例行检测左侧新信号
            m = re.match(r"\s*assign\s+(\w+)", raw)
            if m:
                sig = m.group(1)
                if sig not in known:
                    issues.append(LintIssue(
                        rule="implicit_wire",
                        line=idx + 1,
                        message=f"Implicit wire '{sig}' used in assignment",
                        severity="error",
                        fix=f"declare_wire:{sig}",
                    ))
            # 子模块输出端口连线 .PORT(sig)
            for sm in re.finditer(r"\.(\w+)\s*\((\w+)\)", raw):
                sig = sm.group(2)
                if sig not in known and not sig.isdigit():
                    issues.append(LintIssue(
                        rule="implicit_wire",
                        line=idx + 1,
                        message=f"Implicit wire '{sig}' used in port connection",
                        severity="error",
                        fix=f"declare_wire:{sig}",
                    ))
        return issues

    def _check_multi_driven(self, info: "VerilogLinter._ModuleInfo", lines: List[str]) -> List[LintIssue]:
        issues = []
        for sig, drivers in info.assigned.items():
            # 过滤掉 always comb 中同一信号多行（如 if/else 分支），只算 1 个驱动源
            comb_blocks: Set[int] = set()
            seq_blocks: Set[int] = set()
            assigns = 0
            for line_no, ctx in drivers:
                if ctx == "assign":
                    assigns += 1
                elif ctx == "comb":
                    # 属于哪个 always 块
                    for start, end, sens, body in info.always_blocks:
                        if start <= line_no <= end:
                            comb_blocks.add(start)
                            break
                else:
                    for start, end, sens, body in info.always_blocks:
                        if start <= line_no <= end:
                            seq_blocks.add(start)
                            break

            total = assigns + (1 if comb_blocks else 0) + (1 if seq_blocks else 0)
            # logic/reg-typed signals support the standard SV pattern of a comb
            # default plus a sequential update (e.g., next-state logic). Only
            # flag when there are multiple drivers of the *same* kind or more
            # than 2 total.
            vartype = info.declared.get(sig, ("logic", 0))[0]
            is_logic_like = vartype in ("logic", "reg")
            if is_logic_like and total == 2 and len(comb_blocks) == 1 and len(seq_blocks) == 1:
                continue
            if total > 1:
                issues.append(LintIssue(
                    rule="multi_driven",
                    line=drivers[0][0] + 1,
                    message=f"Signal '{sig}' has multiple drivers (assign={assigns}, comb blocks={len(comb_blocks)}, seq blocks={len(seq_blocks)})",
                    severity="error",
                ))
        return issues

    def _check_unused_signals(self, info: "VerilogLinter._ModuleInfo", lines: List[str]) -> List[LintIssue]:
        issues = []
        for name in list(info.declared.keys()):
            if name not in info.referenced and name not in info.assigned:
                # 可能是输出端口仅被驱动（assigned 不含 output reg 在 always 中的驱动）
                if name in info.assigned:
                    continue
                issues.append(LintIssue(
                    rule="unused_signal",
                    line=info.start_line + 1,
                    message=f"Signal '{name}' is declared but never used",
                    severity="warning",
                ))
        return issues

    def _check_blocking_in_seq(self, info: "VerilogLinter._ModuleInfo", lines: List[str]) -> List[LintIssue]:
        issues = []
        for start, end, sens, body in info.always_blocks:
            if "posedge" not in sens and "negedge" not in sens:
                continue
            for bl in body:
                raw = lines[bl]
                # 排除注释行
                if raw.strip().startswith("//"):
                    continue
                for m in re.finditer(r"(\w+)\s*(?:\[[^\]]+\])?\s*=(?!=)", raw):
                    # 跳过 for 循环变量和 integer 声明
                    if re.search(r"\binteger\s+\w+\s*=" , raw):
                        continue
                    if re.search(r"\bfor\s*\(", raw):
                        continue
                    issues.append(LintIssue(
                        rule="blocking_in_seq",
                        line=bl + 1,
                        message=f"Blocking assignment '=' in sequential block for '{m.group(1)}'",
                        severity="warning",
                        fix="change_to_nonblocking",
                    ))
        return issues

    def _check_latch_risk(self, info: "VerilogLinter._ModuleInfo", lines: List[str]) -> List[LintIssue]:
        issues = []
        for start, end, sens, body in info.always_blocks:
            if "posedge" in sens or "negedge" in sens:
                continue

            block_lines = [(bl, lines[bl]) for bl in body if start <= bl <= end]

            # 收集默认赋值（always 块开头到第一个 if/case 之前的赋值）
            default_assigned: Set[str] = set()
            for bl, raw in block_lines:
                if re.search(r"\b(if|case[zx]?)\s*\(", raw):
                    break
                for m in re.finditer(r"(\w+)\s*(?:\[[^\]]+\])?\s*(?:=(?!=)|<=)", raw):
                    default_assigned.add(m.group(1))

            # 解析 if/else 结构并检查 latch
            if_indices = [idx for idx, (bl, raw) in enumerate(block_lines) if re.search(r"\bif\s*\(", raw)]
            for if_idx in if_indices:
                # 向前扫描，找到这个 if 语句管辖的 if_body 和 else_body
                if_body, else_body, has_else = self._extract_if_else_bodies(block_lines, if_idx)
                if not has_else:
                    # 没有 else，检查 if_body 中的赋值是否都在 default 中
                    for sig in if_body:
                        if sig not in default_assigned:
                            issues.append(LintIssue(
                                rule="latch_risk",
                                line=block_lines[if_idx][0] + 1,
                                message=f"Potential latch: signal '{sig}' assigned in 'if' but missing 'else' branch and no default assignment",
                                severity="warning",
                                fix=f"latch_default:{sig}:{start}",
                            ))
                else:
                    # 有 else，检查两侧差异；忽略空的 else_body（即只有 begin/end 或没有赋值）
                    if_else_only = if_body - else_body
                    else_if_only = else_body - if_body
                    for sig in if_else_only:
                        if sig not in default_assigned:
                            issues.append(LintIssue(
                                rule="latch_risk",
                                line=block_lines[if_idx][0] + 1,
                                message=f"Potential latch: signal '{sig}' assigned in 'if' but not in matching 'else' (add default assignment at block top)",
                                severity="warning",
                                fix=f"latch_default:{sig}:{start}",
                            ))
                    for sig in else_if_only:
                        if sig not in default_assigned:
                            issues.append(LintIssue(
                                rule="latch_risk",
                                line=block_lines[if_idx][0] + 1,
                                message=f"Potential latch: signal '{sig}' assigned in 'else' but not in matching 'if' (add default assignment at block top)",
                                severity="warning",
                                fix=f"latch_default:{sig}:{start}",
                            ))

            # case 没有 default
            case_lines: List[int] = []
            for bl, raw in block_lines:
                if re.search(r"\bcase[zx]?\s*\(", raw):
                    case_lines.append(bl)
            for cl in case_lines:
                has_default = False
                case_assigned: Set[str] = set()
                for j in range(cl + 1, min(end, cl + 200) + 1):
                    raw = lines[j]
                    if re.search(r"\bdefault\b", raw):
                        has_default = True
                        break
                    if re.search(r"\bendcase\b", raw):
                        break
                    for m in re.finditer(r"(\w+)\s*(?:\[[^\]]+\])?\s*(?:=(?!=)|<=)", raw):
                        case_assigned.add(m.group(1))
                if not has_default:
                    for sig in case_assigned:
                        if sig not in default_assigned:
                            issues.append(LintIssue(
                                rule="latch_risk",
                                line=cl + 1,
                                message=f"Potential latch: 'case' without 'default' in comb block, signal '{sig}' may infer latch",
                                severity="warning",
                                fix=f"latch_default:{sig}:{start}",
                            ))
        return issues

    def _extract_if_else_bodies(self, block_lines: List[Tuple[int, str]], if_idx: int) -> Tuple[Set[str], Set[str], bool]:
        """提取 if/else 语句两侧 body 中赋值的信号名。返回 (if_body_set, else_body_set, has_else)。"""
        if_body: Set[str] = set()
        else_body: Set[str] = set()
        has_else = False

        # 从 if 语句后开始扫描，使用 begin/end 深度计数器
        depth = 0
        in_else = False
        target = if_body
        i = if_idx + 1
        while i < len(block_lines):
            _, raw = block_lines[i]
            stripped = raw.strip()

            # begin/end 计数
            # 注意：这行可能同时包含 begin 和 end
            depth += stripped.count("begin")
            depth -= stripped.count("end")

            # 检测 else（同一深度层级）
            if depth == 0 and re.search(r"\belse\b", stripped):
                has_else = True
                in_else = True
                target = else_body
                i += 1
                continue

            # 提取赋值 LHS
            for m in re.finditer(r"(\w+)\s*(?:\[[^\]]+\])?\s*(?:=(?!=)|<=)", raw):
                target.add(m.group(1))

            # 遇到下一个同级 if 或 case，或者深度回到 -1（结束当前 if）则退出
            # 简单判定：如果 depth < 0，说明这行的 end 结束了外层的 begin，if_body 结束
            if depth < 0:
                break

            i += 1
        return if_body, else_body, has_else

    def _check_width_mismatch(self, info: "VerilogLinter._ModuleInfo", lines: List[str]) -> List[LintIssue]:
        issues = []
        # 简单启发式：assign lhs = rhs;
        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx]
            m = re.match(r"\s*assign\s+(\w+(?:\[[^\]]+\])?)\s*=\s*(.+);", raw)
            if m:
                lhs = m.group(1)
                rhs = m.group(2)
                lw = self._infer_width(lhs, info)
                rw = self._infer_width(rhs, info)
                if lw is not None and rw is not None and lw != rw:
                    issues.append(LintIssue(
                        rule="width_mismatch",
                        line=idx + 1,
                        message=f"Width mismatch: left={lw}, right={rw} in assignment",
                        severity="warning",
                    ))
        return issues

    # -----------------------------------------------------------------
    # Fixer
    # -----------------------------------------------------------------
    def _apply_fixes(self, lines: List[str], issues: List[LintIssue], modules: Dict[str, "VerilogLinter._ModuleInfo"]) -> str:
        out = list(lines)
        # 1. 先处理行内替换（此时行号与 issues 一致）
        for issue in issues:
            if issue.rule == "blocking_in_seq" and issue.fix == "change_to_nonblocking":
                line_idx = issue.line - 1
                if 0 <= line_idx < len(out):
                    out[line_idx] = re.sub(r"(\w+(?:\s*\[[^\]]+\])?)\s*=\s*(?!=)", r"\1 <= ", out[line_idx], count=1)

        # 2. default_nettype 插入顶部
        dn_issues = [i for i in issues if i.rule == "default_nettype"]
        if dn_issues:
            out.insert(0, "`default_nettype none")

        running_offset = 1 if dn_issues else 0

        # 3. latch_risk -> 在 always 块 begin 后插入默认赋值
        latch_fixes = [i for i in issues if i.rule == "latch_risk" and i.fix]
        latch_by_always: Dict[int, Set[str]] = {}
        for issue in latch_fixes:
            parts = issue.fix.split(":")
            if len(parts) == 3:
                sig = parts[1]
                always_start = int(parts[2])
                latch_by_always.setdefault(always_start, set()).add(sig)

        for always_start in sorted(latch_by_always.keys(), reverse=True):
            insert_pos = always_start + 1 + running_offset
            mod_name = self._module_at_line(always_start, modules)
            mod_info = modules.get(mod_name)
            always_line = lines[always_start]
            base_indent = len(always_line) - len(always_line.lstrip())
            inner_indent = " " * (base_indent + 4)
            new_lines = []
            for sig in sorted(latch_by_always[always_start]):
                width = mod_info.declared.get(sig, ("logic", 1))[1] if mod_info else 1
                default_val = f"1'b0" if width == 1 else f"{{{width}{{1'b0}}}}"
                new_lines.append(f"{inner_indent}{sig} = {default_val};")
            for line in reversed(new_lines):
                out.insert(insert_pos, line)
            running_offset += len(new_lines)

        # 4. implicit wire -> 在模块内部声明处插入 logic
        wire_fixes = [i for i in issues if i.fix and i.fix.startswith("declare_wire:")]
        # 按模块分组
        wires_by_mod: Dict[str, Set[str]] = {}
        for issue in wire_fixes:
            sig = issue.fix.split(":", 1)[1]
            mod_name = self._module_at_line(issue.line - 1, modules)
            wires_by_mod.setdefault(mod_name, set()).add(sig)

        for mod_name, sigs in wires_by_mod.items():
            info = modules[mod_name]
            insert_pos = info.start_line + 1 + running_offset
            # 找到 ); 后的位置
            for idx in range(info.start_line + running_offset, info.end_line + running_offset + 1):
                if idx < len(out) and re.match(r"\s*\);\s*$", out[idx]):
                    insert_pos = idx + 1
                    break
            decls = [f"    logic {s};" for s in sorted(sigs)]
            for d in reversed(decls):
                out.insert(insert_pos, d)
            running_offset += len(decls)

        return "\n".join(out)
    def _width_from_range(self, range_str: Optional[str]) -> int:
        if not range_str:
            return 1
        m = re.match(r"(\d+)\s*:\s*(\d+)", range_str.strip())
        if m:
            return int(m.group(1)) - int(m.group(2)) + 1
        return 1

    def _extract_ids(self, text: str) -> Set[str]:
        return set(re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", text)) - {
            "module", "endmodule", "input", "output", "inout", "wire", "reg", "logic",
            "assign", "always", "begin", "end", "if", "else", "case", "casex", "casez",
            "endcase", "for", "generate", "endgenerate", "genvar", "integer",
            "parameter", "localparam", "posedge", "negedge", "or", "and", "not",
            "default", "none", "defparam",
        }

    def _module_at_line(self, line_idx: int, modules: Dict[str, "VerilogLinter._ModuleInfo"]) -> str:
        for name, info in modules.items():
            if info.start_line <= line_idx <= info.end_line:
                return name
        return ""

    def _infer_width(self, expr_str: str, info: "VerilogLinter._ModuleInfo") -> Optional[int]:
        """启发式推断表达式宽度。"""
        expr_str = expr_str.strip()
        # 直接信号名
        if expr_str in info.declared:
            return info.declared[expr_str][1]
        # 带下标
        m = re.match(r"(\w+)\[(\d+)\]", expr_str)
        if m and m.group(1) in info.declared:
            return 1
        # 位选
        m = re.match(r"(\w+)\[(\d+):(\d+)\]", expr_str)
        if m and m.group(1) in info.declared:
            return int(m.group(2)) - int(m.group(3)) + 1
        # part-select
        m = re.match(r"(\w+)\[\S+\s*\+:\s*(\d+)\]", expr_str)
        if m and m.group(1) in info.declared:
            return int(m.group(2))
        # 拼接
        if expr_str.startswith("{"):
            parts = re.findall(r"([^,{}]+)", expr_str)
            total = 0
            for p in parts:
                w = self._infer_width(p.strip(), info)
                if w is None:
                    return None
                total += w
            return total
        # 常数 8'd123
        m = re.match(r"(\d+)'[bdoh]\d+", expr_str, re.I)
        if m:
            return int(m.group(1))
        # 纯数字
        if re.match(r"^\d+$", expr_str):
            return max(int(expr_str).bit_length(), 1)
        return None

    # -----------------------------------------------------------------
    # Rule: unregistered_output — 输出端口仅有组合逻辑驱动
    # -----------------------------------------------------------------
    def _check_unregistered_output(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检测 output 端口是否仅被组合逻辑（assign / always @(*)）驱动。

        若一个 output 从未在时序 always 块中被赋值，且存在组合驱动，则告警。
        """
        issues: List[LintIssue] = []

        # 只检查有 always @(posedge/negedge) 时序块的模块
        has_seq = any(
            "posedge" in sens or "negedge" in sens
            for _, _, sens, _ in info.always_blocks
        )
        if not has_seq:
            return issues

        # 识别真正的 output 端口
        output_ports: Set[str] = set()
        for name, (vartype, _) in info.declared.items():
            if vartype == "output" and name in info.ports:
                output_ports.add(name)

        # 收集在时序 always 块中被驱动的信号
        seq_driven: Set[str] = set()
        for start, end, sens, body in info.always_blocks:
            if "posedge" not in sens and "negedge" not in sens:
                continue
            for bl in body:
                raw = lines[bl]
                for m in re.finditer(r"(\w+)\s*(?:\[[^\]]+\])?\s*<=", raw):
                    seq_driven.add(m.group(1))

        # 收集在组合 always 块中被驱动的信号
        comb_driven: Set[str] = set()
        for start, end, sens, body in info.always_blocks:
            if "posedge" in sens or "negedge" in sens:
                continue
            for bl in body:
                raw = lines[bl]
                for m in re.finditer(r"(\w+)\s*(?:\[[^\]]+\])?\s*(?:=(?!=)|<=)", raw):
                    comb_driven.add(m.group(1))

        # 收集 assign 驱动的信号
        assign_driven: Dict[str, str] = {}  # lhs -> rhs text
        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx]
            assign_m = re.match(r"\s*assign\s+(\w+)\s*=\s*(.+);", raw)
            if assign_m:
                assign_driven[assign_m.group(1)] = assign_m.group(2)

        def _is_seq_driven(sig: str, visited: Set[str]) -> bool:
            """递归判断信号是否（直接或间接）被时序逻辑驱动。"""
            if sig in visited:
                return False
            visited.add(sig)
            if sig in seq_driven:
                return True
            # 如果通过 assign 驱动，追踪其源
            if sig in assign_driven:
                rhs_ids = self._extract_ids(assign_driven[sig])
                for rhs_sig in rhs_ids:
                    if _is_seq_driven(rhs_sig, visited):
                        return True
            return False

        def _is_pure_comb(sig: str, visited: Set[str]) -> bool:
            """递归判断信号是否（仅）被组合逻辑驱动。"""
            if sig in visited:
                return False
            visited.add(sig)
            if sig in seq_driven:
                return False
            if sig in comb_driven:
                return True
            if sig in assign_driven:
                rhs_ids = self._extract_ids(assign_driven[sig])
                if not rhs_ids:
                    return True
                return all(_is_pure_comb(s, visited) for s in rhs_ids)
            return False

        # 报告仅被组合逻辑驱动的 output
        for sig in sorted(output_ports):
            if _is_pure_comb(sig, set()):
                if "valid" in sig.lower() or "ready" in sig.lower():
                    continue
                issues.append(LintIssue(
                    rule="unregistered_output",
                    line=info.start_line + 1,
                    message=f"Output '{sig}' is driven purely by combinational logic in a clocked module. "
                            f"Consider registering this output for pipeline correctness.",
                    severity="warning",
                ))
        return issues

    # -----------------------------------------------------------------
    # Rule: valid_ready_protocol — valid/ready 握手协议违例
    # -----------------------------------------------------------------
    def _check_valid_ready_protocol(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检查 valid/ready 握手协议的正确性。

        规则：
        1. valid 输出应被时序逻辑驱动
        2. ready 输出应被组合逻辑驱动
        """
        issues: List[LintIssue] = []

        has_seq_block = any(
            "posedge" in sens or "negedge" in sens
            for _, _, sens, _ in info.always_blocks
        )
        if not has_seq_block:
            return issues

        # 识别 valid/ready output 端口
        valid_outputs: List[Tuple[str, int]] = []
        ready_outputs: List[Tuple[str, int]] = []

        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx]
            out_m = re.match(r"\s*output\s+(?:reg\s+)?(?:\[[^\]]+\]\s*)?(\w+)\s*,?\s*$", raw)
            if out_m:
                name = out_m.group(1)
                if "valid" in name.lower():
                    valid_outputs.append((name, idx))
                if "ready" in name.lower():
                    ready_outputs.append((name, idx))

        # 收集时序/组合驱动信号
        seq_driven: Set[str] = set()
        comb_driven: Set[str] = set()
        # comb 块中的依赖关系: sig -> list of rhs signal names
        comb_deps: Dict[str, List[str]] = {}

        for start, end, sens, body in info.always_blocks:
            is_seq = "posedge" in sens or "negedge" in sens
            for bl in body:
                raw = lines[bl]
                for m in re.finditer(r"(\w+)\s*(?:\[[^\]]+\])?\s*(?:=(?!=)|<=)", raw):
                    lhs = m.group(1)
                    if is_seq:
                        seq_driven.add(lhs)
                    else:
                        comb_driven.add(lhs)
                        # Extract RHS expression (everything after first = or <=)
                        rhs_text = raw[m.end():] if m.end() < len(raw) else ""
                        # Remove trailing semicolon/comments
                        rhs_clean = rhs_text.split(";")[0].split("//")[0]
                        rhs_ids = self._extract_ids(rhs_clean)
                        comb_deps.setdefault(lhs, []).extend(rhs_ids)

        # 收集 assign 驱动关系
        assign_driven: Dict[str, str] = {}
        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx]
            assign_m = re.match(r"\s*assign\s+(\w+)\s*=\s*(.+);", raw)
            if assign_m:
                assign_driven[assign_m.group(1)] = assign_m.group(2)

        def _is_pure_comb(sig: str, visited: Set[str]) -> bool:
            if sig in visited:
                return False
            visited.add(sig)
            if sig in seq_driven:
                return False
            if sig in comb_driven:
                # Check if any dependency is seq-driven (directly or via assign)
                deps = comb_deps.get(sig, [])
                if not deps:
                    return True
                return all(_is_pure_comb(s, visited) for s in deps)
            if sig in assign_driven:
                rhs_ids = self._extract_ids(assign_driven[sig])
                if not rhs_ids:
                    return True
                return all(_is_pure_comb(s, visited) for s in rhs_ids)
            return False

        # 规则 1: valid 输出应被时序驱动（不应该是纯组合）
        for name, line_no in valid_outputs:
            if _is_pure_comb(name, set()):
                issues.append(LintIssue(
                    rule="valid_ready_protocol",
                    line=line_no + 1,
                    message=f"Output '{name}' (valid) is driven by combinational logic only. "
                            f"Valid outputs should be registered.",
                    severity="error",
                ))

        # 规则 2: ready 输出应被组合驱动（不应只在时序中驱动）
        for name, line_no in ready_outputs:
            if name in seq_driven and name not in comb_driven and name not in assign_driven:
                issues.append(LintIssue(
                    rule="valid_ready_protocol",
                    line=line_no + 1,
                    message=f"Output '{name}' (ready) is driven by sequential logic only. "
                            f"Ready outputs should be combinational for proper back-pressure.",
                    severity="error",
                ))

        return issues

    # -----------------------------------------------------------------
    # Rule: constant_width_consistency — case 标签位宽一致性
    # -----------------------------------------------------------------
    def _check_constant_width_consistency(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检查 case 标签中常量的位宽是否与选择器一致。

        例如选择器是 2-bit，但标签用 1'd0、1'd1、2'd2、2'd3，
        应该统一用 2'd0、2'd1、2'd2、2'd3。
        """
        issues: List[LintIssue] = []

        for start, end, sens, body in info.always_blocks:
            # 找到 case 行和对应的 case 表达式
            for bl_idx in range(len(body)):
                bl = body[bl_idx]
                raw = lines[bl]
                case_m = re.match(r"\s*case\s*\((.+)\)\s*$", raw.strip())
                if not case_m:
                    # Also match inline: "case (expr)"
                    case_m = re.search(r"\bcase\s*\((.+)\)", raw)
                if case_m:
                    sel_expr_str = case_m.group(1).strip()
                    sel_width = self._infer_width(sel_expr_str, info)

                    # 扫描后续的 case 标签行
                    for j in range(bl_idx + 1, len(body)):
                        label_line = body[j]
                        label_raw = lines[label_line]
                        # 匹配 case 标签: 2'd0: 或 1'd0:
                        label_m = re.match(r"\s*(\d+)'([bdoh])(\d+)\s*:", label_raw.strip())
                        if label_m:
                            label_width = int(label_m.group(1))
                            if sel_width is not None and label_width != sel_width:
                                issues.append(LintIssue(
                                    rule="constant_width_consistency",
                                    line=label_line + 1,
                                    message=f"Case label width {label_width}'d doesn't match "
                                            f"selector width {sel_width}'d. Use {sel_width}'d{label_m.group(3)}.",
                                    severity="warning",
                                    fix=f"widen_case_label:{label_width}:{sel_width}",
                                ))
                        if re.search(r"\bendcase\b", label_raw):
                            break

        return issues

    # -----------------------------------------------------------------
    # Rule: narrow_const_comparison — 1 位信号与 1'd1 比较
    # -----------------------------------------------------------------
    def _check_narrow_const_comparison(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检查 1 位信号是否与 1'd1 做 == 比较（冗余写法）。

        例如：shift_amount[0] == 1'd1 — 1 位信号本身就是布尔值，
        直接写 shift_amount[0] 即可。
        """
        issues: List[LintIssue] = []

        for start, end, sens, body in info.always_blocks:
            for bl in body:
                raw = lines[bl]
                # 匹配 signal == 1'd1 或 1'd1 == signal 模式
                for m in re.finditer(r"(\w+(?:\[\d+\]))\s*==\s*1'[bdoh]1\b", raw):
                    issues.append(LintIssue(
                        rule="narrow_const_comparison",
                        line=bl + 1,
                        message=f"Redundant comparison '{m.group(1)} == 1\\'d1'. "
                                f"Use '{m.group(1)}' directly.",
                        severity="warning",
                    ))
                for m in re.finditer(r"1'[bdoh]1\s*==\s*(\w+(?:\[\d+\]))", raw):
                    issues.append(LintIssue(
                        rule="narrow_const_comparison",
                        line=bl + 1,
                        message=f"Redundant comparison '1\\'d1 == {m.group(1)}'. "
                                f"Use '{m.group(1)}' directly.",
                        severity="warning",
                    ))
                # 也检查 == 1'd0 / == 0 的 1 位信号比较
                for m in re.finditer(r"(\w+(?:\[\d+\]))\s*==\s*1'[bdoh]0\b", raw):
                    issues.append(LintIssue(
                        rule="narrow_const_comparison",
                        line=bl + 1,
                        message=f"Redundant comparison '{m.group(1)} == 1\\'d0'. "
                                f"Use '~{m.group(1)}' directly.",
                        severity="warning",
                    ))

        return issues

    # -----------------------------------------------------------------
    # Rule: incomplete_if_else_chain — if-else 链不完整
    # -----------------------------------------------------------------
    def _check_incomplete_if_else_chain(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检查 if-else 链中的 } else begin ... if ... end 模式。

        专业 RTL 应该用 } else if (...) begin 而非 } else begin if (...) end。
        后者增加了不必要的缩进层级。
        """
        issues: List[LintIssue] = []

        for idx in range(len(lines)):
            raw = lines[idx].strip()
            # 匹配 } else begin { 模式（即 else 后紧跟 begin，下一行是 if）
            if re.search(r"\}\s*else\s+begin\s*$", raw) or re.match(r"end\s+else\s+begin\s*$", raw):
                # 检查下一行是否是 if
                if idx + 1 < len(lines):
                    next_raw = lines[idx + 1].strip()
                    if re.match(r"if\s*\(", next_raw):
                        issues.append(LintIssue(
                            rule="incomplete_if_else_chain",
                            line=idx + 1,
                            message="'} else begin' followed by 'if' on next line. "
                                    "Consider '} else if (' for cleaner nesting.",
                            severity="warning",
                        ))

        return issues

    # -----------------------------------------------------------------
    # Rule: style_mux_chain — 级联三元运算符建议用 case
    # -----------------------------------------------------------------
    def _check_style_mux_chain(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检测 assign 语句中的级联三元运算符（?: 链），建议用 case 替代。

        超过 3 个级联三元运算符的可读性不如 case 语句。
        """
        issues: List[LintIssue] = []

        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx]
            assign_m = re.match(r"\s*assign\s+(\w+)\s*=\s*(.+);", raw)
            if assign_m:
                rhs = assign_m.group(2)
                # 数三元运算符数量
                mux_count = rhs.count("?")
                if mux_count >= 4:
                    issues.append(LintIssue(
                        rule="style_mux_chain",
                        line=idx + 1,
                        message=f"Signal '{assign_m.group(1)}' uses {mux_count} cascaded ternary operators. "
                                f"Consider using 'case' for readability.",
                        severity="warning",
                    ))

        return issues

    # -----------------------------------------------------------------
    # Rule: style_nested_if — 深层 if-else 嵌套建议扁平化
    # -----------------------------------------------------------------
    def _check_style_nested_if(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检测 overly deep if-else 嵌套（> 4 级）。

        专业 RTL 通常用扁平的 if/else if/else 或 case 替代。
        """
        issues: List[LintIssue] = []

        for start, end, sens, body in info.always_blocks:
            # 扫描 always 块，跟踪 if 嵌套深度
            for bl in body:
                raw = lines[bl]
                # 简单深度估计：计算前缀空格
                indent = len(raw) - len(raw.lstrip())
                # 假设每级缩进 4 空格
                depth = indent // 4
                if depth >= 5 and re.search(r"\bif\s*\(", raw):
                    issues.append(LintIssue(
                        rule="style_nested_if",
                        line=bl + 1,
                        message=f"Deep if-else nesting ({depth} levels) in always block. "
                                f"Consider flattening with 'else if' or using 'case'.",
                        severity="warning",
                    ))

        return issues

    # -----------------------------------------------------------------
    # Rule: signed_mix — 有符号与无符号信号混合运算
    # -----------------------------------------------------------------
    def _check_signed_mix(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检测 $signed 与普通信号引用在同一风险表达式中混合。"""
        issues: List[LintIssue] = []
        issues.extend(self._check_signed_binary_op_mix(
            info,
            lines,
            ops={"+", "-", "*", "/", "%", "<<", ">>", ">>>", "<", "<=", ">", ">=", "==", "!="},
            rule="signed_mix",
            summary="operate",
            guidance="Use $signed(...) or $unsigned(...) consistently on both operands to clarify intent.",
        ))
        return issues

    # -----------------------------------------------------------------
    # Rule: signed_shift — signed/unsigned 右移意图不清晰
    # -----------------------------------------------------------------
    def _check_signed_shift(
        self, info: "VerilogLinter._ModuleInfo", lines: List[str]
    ) -> List[LintIssue]:
        """检测有符号右移/算术右移的意图是否明确。"""
        issues: List[LintIssue] = []
        def _lhs_name(lhs: str) -> str:
            return lhs.split("[", 1)[0]

        def _expr_is_signed(expr: str) -> bool:
            return "$signed(" in expr or re.search(r"\bSRA\s*\(", expr) is not None

        def _is_declared_signed(name: str) -> bool:
            if name in info.signed_declared:
                return True
            decl = info.declared.get(name)
            if decl is None:
                return False
            vartype, _ = decl
            return vartype in {"signed", "reg_signed"}

        def _scan_assignment(lhs: str, rhs: str, line_no: int) -> None:
            lhs_name = _lhs_name(lhs)
            rhs = rhs.split("//", 1)[0]
            op = ">>>" if ">>>" in rhs else ">>" if ">>" in rhs else ""
            if not op:
                return
            shift_pos = rhs.find(op)
            lhs_expr = rhs[:shift_pos].strip()

            def _expr_looks_signed(expr: str) -> bool:
                if _expr_is_signed(expr):
                    return True
                for token in re.findall(r"\b[a-zA-Z_]\w*\b", expr):
                    if _is_declared_signed(token):
                        return True
                return False

            lhs_signed = _expr_looks_signed(lhs_expr)
            if op == ">>>":
                if not lhs_signed:
                    issues.append(LintIssue(
                        rule="signed_shift",
                        line=line_no,
                        message=f"Expression for '{lhs_name}' uses '>>>' but its left operand is not explicitly signed. "
                                f"Use SRA(...), or cast the left operand with $signed(...) to make the arithmetic shift intent clear.",
                        severity="warning",
                    ))
                return
            if lhs_signed:
                issues.append(LintIssue(
                    rule="signed_shift",
                    line=line_no,
                    message=f"Signed left operand in '{lhs_name}' is shifted with '>>'. Prefer SRA(...), '>>>', or wrap the left operand with $signed(...) "
                            f"so the shift intent is explicit across simulation and emitted RTL.",
                    severity="warning",
                ))

        for start, end, sens, body in info.always_blocks:
            for bl in body:
                raw = lines[bl].split("//", 1)[0]
                m = re.search(r"(\w+)\s*(?:\[[^\]]+\])?\s*(?:=(?!=)|<=)\s*(.+);", raw)
                if m:
                    _scan_assignment(m.group(1), m.group(2), bl + 1)

        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx].split("//", 1)[0]
            assign_m = re.match(r"\s*assign\s+(\w+)\s*=\s*(.+);", raw)
            if assign_m:
                _scan_assignment(assign_m.group(1), assign_m.group(2), idx + 1)

        return issues

    def _check_signed_binary_op_mix(
        self,
        info: "VerilogLinter._ModuleInfo",
        lines: List[str],
        *,
        ops: Set[str],
        rule: str,
        summary: str,
        guidance: str,
    ) -> List[LintIssue]:
        """Heuristically detect signed/unsigned mix for binary operators."""

        issues: List[LintIssue] = []
        seen: Set[tuple[int, str, str, str, str]] = set()

        def _lhs_name(lhs: str) -> str:
            return lhs.split("[", 1)[0]

        def _is_declared_signed(name: str) -> bool:
            if name in info.signed_declared:
                return True
            decl = info.declared.get(name)
            if decl is None:
                return False
            vartype, _ = decl
            return vartype in {"signed", "reg_signed"}

        def _token_is_numeric(token: str) -> bool:
            token = token.strip()
            return bool(re.match(r"^(?:\d+)?'[bdhoBDHO][0-9a-fA-F_xXzZ]+$", token) or re.match(r"^\d+$", token))

        def _strip_outer_parens(expr: str) -> str:
            expr = expr.strip()
            while expr.startswith("(") and expr.endswith(")"):
                depth = 0
                balanced = True
                for idx, ch in enumerate(expr):
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0 and idx != len(expr) - 1:
                            balanced = False
                            break
                if not balanced or depth != 0:
                    break
                expr = expr[1:-1].strip()
            return expr

        def _split_binary_expr(expr: str) -> Optional[tuple[str, str, str]]:
            expr = _strip_outer_parens(expr)
            for op in ("<<<", ">>>", "<<", ">>", "<=", ">=", "==", "!=", "<", ">", "*", "+", "-", "/", "%"):
                depth = 0
                idx = 0
                while idx <= len(expr) - len(op):
                    ch = expr[idx]
                    if ch == "(":
                        depth += 1
                        idx += 1
                        continue
                    if ch == ")":
                        depth = max(depth - 1, 0)
                        idx += 1
                        continue
                    if depth == 0 and expr.startswith(op, idx):
                        lhs = expr[:idx].strip()
                        rhs = expr[idx + len(op):].strip()
                        if lhs and rhs:
                            return lhs, op, rhs
                    idx += 1
            return None

        def _expr_looks_signed(expr: str) -> Optional[bool]:
            expr = _strip_outer_parens(expr)
            if not expr:
                return None
            if "$unsigned(" in expr:
                return False
            if "$signed(" in expr or re.search(r"\bSRA\s*\(", expr):
                return True
            split = _split_binary_expr(expr)
            if split is not None:
                lhs, _, rhs = split
                lhs_signed = _expr_looks_signed(lhs)
                rhs_signed = _expr_looks_signed(rhs)
                if lhs_signed is None or rhs_signed is None:
                    return None
                if lhs_signed == rhs_signed:
                    return lhs_signed
                return None
            tokens = re.findall(r"\b[a-zA-Z_]\w*\b", expr)
            signed_tokens = [token for token in tokens if _is_declared_signed(token)]
            if signed_tokens:
                unsigned_tokens = [
                    token for token in tokens
                    if token not in signed_tokens and token not in {"signed", "unsigned", "SRA"}
                ]
                if unsigned_tokens:
                    return None
                return True
            if _token_is_numeric(expr):
                return False
            if tokens:
                return False
            return None

        def _scan_assignment(lhs: str, rhs: str, line_no: int) -> None:
            lhs_name = _lhs_name(lhs)
            rhs = rhs.split("//", 1)[0].strip()
            split = _split_binary_expr(rhs)
            if split is None:
                return
            left_expr, op, right_expr = split
            if op not in ops:
                return

            left_signed = _expr_looks_signed(left_expr)
            right_signed = _expr_looks_signed(right_expr)
            if left_signed is None or right_signed is None or left_signed == right_signed:
                return

            signed_expr, unsigned_expr = (
                (left_expr, right_expr) if left_signed else (right_expr, left_expr)
            )
            key = (line_no, op, lhs_name, signed_expr, unsigned_expr)
            if key in seen:
                return
            seen.add(key)
            issues.append(LintIssue(
                rule=rule,
                line=line_no,
                message=f"Signed expression '{signed_expr}' and unsigned expression '{unsigned_expr}' "
                        f"are mixed with '{op}' while driving '{lhs_name}'. {guidance}",
                severity="warning",
            ))

        for start, end, sens, body in info.always_blocks:
            for bl in body:
                raw = lines[bl].split("//", 1)[0]
                m = re.search(r"(\w+)\s*(?:\[[^\]]+\])?\s*(?:=(?!=)|<=)\s*(.+);", raw)
                if m:
                    _scan_assignment(m.group(1), m.group(2), bl + 1)

        for idx in range(info.start_line, info.end_line + 1):
            raw = lines[idx].split("//", 1)[0]
            assign_m = re.match(r"\s*assign\s+(\w+)\s*=\s*(.+);", raw)
            if assign_m:
                _scan_assignment(assign_m.group(1), assign_m.group(2), idx + 1)

        return issues
