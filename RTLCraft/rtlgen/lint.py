"""
rtlgen.lint — Verilog Linter & Auto-Fixer

针对 rtlgen.codegen 生成的 Verilog 进行后处理验证与自动修复。
支持规则：
    - implicit_wire    : 隐式 wire 检测并补声明
    - multi_driven     : 多重驱动检测
    - unused_signal    : 未使用信号检测
    - blocking_in_seq  : 时序逻辑中阻塞赋值检测
    - latch_risk       : 组合逻辑 latch 风险检测
    - width_mismatch   : 赋值位宽不匹配检测（启发式）
    - default_nettype  : 检查/添加 `default_nettype none
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
        in_always = False
        always_start = 0
        always_sens = ""
        always_body_lines: List[int] = []
        begin_depth = 0

        for idx, raw in enumerate(slice_lines):
            line = raw.strip()
            line_no = offset + idx

            # 端口声明（在模块头中）
            port_re = re.compile(r"\b(input|output|inout)\b(?:\s+reg)?(?:\s*\[([^\]]+)\]\s*)?\s+(\w+)")
            for m in port_re.finditer(raw):
                info.ports.add(m.group(3))
                info.declared[m.group(3)] = (m.group(1), self._width_from_range(m.group(2)))

            # 内部信号声明
            decl_re = re.compile(r"\b(logic|wire|reg)\s+(?:\[([^\]]+)\]\s*)?(\w+)")
            for m in decl_re.finditer(raw):
                info.declared[m.group(3)] = (m.group(1), self._width_from_range(m.group(2)))

            # array 声明: logic [7:0] arr [0:15];
            arr_re = re.compile(r"\b(logic|wire|reg)\s+(?:\[([^\]]+)\]\s*)?(\w+)\s*\[")
            for m in arr_re.finditer(raw):
                info.declared[m.group(3)] = (m.group(1), self._width_from_range(m.group(2)))

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

            # assign 语句
            assign_m = re.match(r"\s*assign\s+(\w+)", raw)
            if assign_m:
                sig = assign_m.group(1)
                info.assigned.setdefault(sig, []).append((line_no, "assign"))
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

        for start, end, sens, body in info.always_blocks:
            is_seq = "posedge" in sens or "negedge" in sens
            for bl in body:
                raw = lines[bl]
                for m in re.finditer(r"(\w+)\s*(?:\[[^\]]+\])?\s*(?:=(?!=)|<=)", raw):
                    if is_seq:
                        seq_driven.add(m.group(1))
                    else:
                        comb_driven.add(m.group(1))

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
                return True
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
