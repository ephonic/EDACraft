"""
rtlgen.codegen — Verilog 代码生成后端

将 rtlgen.core 构建的 AST 与模块层次遍历输出为可综合的 Verilog-2001 代码。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from rtlgen.core import (
    Array,
    ArrayRead,
    ArrayWrite,
    Assign,
    BinOp,
    BitSelect,
    Comment,
    Concat,
    Const,
    Expr,
    ForGenNode,
    GenIfNode,
    GenVar,
    IfNode,
    IndexedAssign,
    LocalParam,
    MemRead,
    MemWrite,
    Memory,
    Module,
    Mux,
    Output,
    PartSelect,
    Ref,
    Reg,
    Signal,
    Slice,
    SubmoduleInst,
    SwitchNode,
    UnaryOp,
)


class VerilogEmitter:
    """Verilog 代码发射器。"""

    def __init__(self, indent: str = "    ", use_sv_always: bool = False):
        self.indent = indent
        self.use_sv_always = use_sv_always
        self.lines: List[str] = []

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def emit(self, module: Module) -> str:
        """生成单个模块的 Verilog 代码。"""
        self.lines = []
        self._emit_module(module)
        return "\n".join(self.lines)

    def emit_with_lint(self, module: Module, auto_fix: bool = False, rules: Optional[List[str]] = None) -> Tuple[str, "LintResult"]:
        """生成 Verilog 并运行 lint，返回 (verilog_text, lint_result)。"""
        from rtlgen.lint import VerilogLinter
        text = self.emit(module)
        linter = VerilogLinter(rules=rules, auto_fix=auto_fix)
        result = linter.lint(text)
        out_text = result.fixed_text if auto_fix and result.fixed_text is not None else text
        return out_text, result

    def emit_design(self, top_module: Module, include_assertions: bool = False) -> str:
        """生成整个设计（包含所有子模块）的 Verilog 代码。

        自动基于模块结构（端口+参数）进行去重，避免同名/同构模块重复输出。
        如果 include_assertions=True，还会为带有 _module_assertions 的模块生成 SVA bind 模块。
        """
        visited: Dict[str, Module] = {}
        order: List[Module] = []

        def _dfs_stmts(stmts: List[Any]):
            for stmt in stmts:
                if isinstance(stmt, SubmoduleInst):
                    dfs(stmt.module)
                elif isinstance(stmt, IfNode):
                    _dfs_stmts(stmt.then_body)
                    _dfs_stmts(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, body in stmt.cases:
                        _dfs_stmts(body)
                    _dfs_stmts(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    _dfs_stmts(stmt.body)
                elif isinstance(stmt, GenIfNode):
                    _dfs_stmts(stmt.then_body)
                    _dfs_stmts(stmt.else_body)

        def dfs(mod: Module):
            type_name = getattr(mod, '_type_name', mod.name)
            if type_name in visited:
                return
            visited[type_name] = mod
            for _, sub in mod._submodules:
                dfs(sub)
            _dfs_stmts(mod._top_level)
            for body in mod._comb_blocks:
                _dfs_stmts(body)
            for _, _, _, _, body in mod._seq_blocks:
                _dfs_stmts(body)
            order.append(mod)

        dfs(top_module)

        # 结构指纹去重：接口（inputs/outputs/params）相同的模块只输出一次
        # 使用 _type_name + 端口结构作为指纹，忽略实例名差异
        def _fingerprint(mod: Module) -> tuple:
            return (
                getattr(mod, '_type_name', mod.name),
                tuple((n, s.width) for n, s in sorted(mod._inputs.items())),
                tuple((n, s.width) for n, s in sorted(mod._outputs.items())),
                tuple(sorted((n, p.value) for n, p in mod._params.items())),
            )

        fingerprint_to_canonical: Dict[tuple, Module] = {}
        name_remap: Dict[str, str] = {}
        id_remap: Dict[int, str] = {}
        deduped_order: List[Module] = []
        for mod in order:
            fp = _fingerprint(mod)
            canonical_name = getattr(fingerprint_to_canonical.get(fp), '_type_name', getattr(fingerprint_to_canonical.get(fp), 'name', mod.name))
            if fp in fingerprint_to_canonical:
                name_remap[mod.name] = canonical_name
                id_remap[id(mod)] = canonical_name
            else:
                fingerprint_to_canonical[fp] = mod
                tname = getattr(mod, '_type_name', mod.name)
                name_remap[mod.name] = tname
                id_remap[id(mod)] = tname
                deduped_order.append(mod)

        self._module_name_remap = name_remap
        self._module_id_remap = id_remap
        try:
            parts = []
            for mod in deduped_order:
                parts.append(self.emit(mod))
                parts.append("")
            if include_assertions:
                from rtlgen.svagen import SVAEmitter
                sva = SVAEmitter()
                for mod in deduped_order:
                    if mod._module_assertions or mod._module_comments:
                        # 只要模块有 assertions 或能被自动检测的握手信号就生成
                        sva_text = sva.emit_assertions(
                            mod,
                            custom_assertions=mod._module_assertions or None,
                        )
                        if sva_text:
                            parts.append(sva_text)
                            parts.append("")
            return "\n".join(parts).strip()
        finally:
            del self._module_name_remap
            if hasattr(self, '_module_id_remap'):
                del self._module_id_remap

    # -----------------------------------------------------------------
    # Module emission
    # -----------------------------------------------------------------
    def _emit_module(self, module: Module):
        # 模块级注释与建议
        if module._module_comments or module._module_suggestions:
            for line in module._module_comments:
                self.lines.append(f"// {line}")
            if module._module_suggestions:
                self.lines.append("// PPA Suggestions:")
                for sug in module._module_suggestions:
                    self.lines.append(f"//   - {sug}")
            self.lines.append("")

        # 先推导哪些 Output 需要在 always 块中被驱动，从而声明为 output reg
        reg_outputs = self._collect_reg_outputs(module)

        # 参数声明：区分可配置的 parameter 和局部的 localparam
        params = list(module._params.values())
        module_params = [p for p in params if not isinstance(p, LocalParam)]
        mod_name = getattr(module, '_type_name', module.name)
        if module_params:
            param_lines = ", ".join(f"parameter {p.name} = {p.value}" for p in module_params)
            self.lines.append(f"module {mod_name} #({param_lines}) (")
        else:
            self.lines.append(f"module {mod_name} (")

        # 端口列表
        ports: List[str] = []
        for sig in module._inputs.values():
            ports.append(self._port_decl("input", sig, reg_outputs))
        for sig in module._outputs.values():
            ports.append(self._port_decl("output", sig, reg_outputs))

        if ports:
            for i, p in enumerate(ports):
                comma = "," if i < len(ports) - 1 else ""
                self.lines.append(f"    {p}{comma}")
        self.lines.append(");")
        self.lines.append("")

        # Memory 声明
        self._emit_memory_decls(module)

        # 内部信号声明
        self._emit_internal_decls(module)

        # 顶层语句（assign、子模块实例等）
        for stmt in module._top_level:
            self._emit_toplevel_stmt(stmt)

        # 子模块隐式实例化（跳过已在 _top_level 中显式实例化的模块）
        explicit_inst_mods = set()
        for stmt in module._top_level:
            if isinstance(stmt, SubmoduleInst):
                explicit_inst_mods.add(id(stmt.module))
        for inst_name, submod in module._submodules:
            if id(submod) in explicit_inst_mods:
                continue
            self._emit_implicit_submodule(inst_name, submod, module)

        # 组合逻辑块
        for body in module._comb_blocks:
            if self._is_simple_comb_block(body):
                self._emit_simple_comb(body)
            else:
                self._emit_always_comb(body)

        # 时序逻辑块
        for clk, rst, reset_async, reset_active_low, body in module._seq_blocks:
            self._emit_always_seq(clk, rst, reset_async, reset_active_low, body)

        self.lines.append("endmodule")

    def _port_decl(self, direction: str, sig: Signal, reg_outputs: set) -> str:
        is_reg = sig.name in reg_outputs
        reg_str = " reg" if is_reg else ""
        if sig.width == 1:
            return f"{direction}{reg_str} {sig.name}"
        return f"{direction}{reg_str} [{sig.width - 1}:0] {sig.name}"

    def _emit_memory_decls(self, module: Module):
        seen: set = set()
        for mem in module._memories.values():
            if mem.name in seen:
                continue
            seen.add(mem.name)
            self.lines.append(f"    reg [{mem.width - 1}:0] {mem.name} [0:{mem.depth - 1}];")
            if mem.init_file:
                self.lines.append(f"    initial begin")
                self.lines.append(f"        $readmemh(\"{mem.init_file}\", {mem.name});")
                self.lines.append(f"    end")
        if module._memories:
            self.lines.append("")

    def _emit_internal_decls(self, module: Module):
        # localparam 声明
        localparams = [p for p in module._params.values() if isinstance(p, LocalParam)]
        for p in localparams:
            self.lines.append(f"    localparam {p.name} = {p.value};")
        if localparams:
            self.lines.append("")

        # internal signals (use logic so they can be driven in both assign and always)
        for sig in module._wires.values():
            # Skip signals that belong to an Array (declared as 2D array below)
            if getattr(sig, '_array_parent', None) is None:
                self.lines.append(self._sig_decl("logic", sig))
        # regs
        for sig in module._regs.values():
            if getattr(sig, '_array_parent', None) is None:
                self.lines.append(self._sig_decl("reg", sig))
        # arrays
        for arr in module._arrays.values():
            vtype = "reg" if arr._vtype is Reg else "logic"
            if arr.width == 1:
                self.lines.append(f"    {vtype} {arr.name} [0:{arr.depth - 1}];")
            else:
                self.lines.append(f"    {vtype} [{arr.width - 1}:0] {arr.name} [0:{arr.depth - 1}];")
        # submodule outputs that are not already declared
        for _, sub in module._submodules:
            for sig in sub._outputs.values():
                if sig.name not in module._wires and sig.name not in module._regs:
                    pass  # implicit signals handled elsewhere or expected to exist
        if module._wires or module._regs or module._arrays:
            self.lines.append("")

    def _sig_decl(self, vtype: str, sig: Signal) -> str:
        if sig.width == 1:
            return f"    {vtype} {sig.name};"
        return f"    {vtype} [{sig.width - 1}:0] {sig.name};"

    # -----------------------------------------------------------------
    # Statements
    # -----------------------------------------------------------------
    def _emit_toplevel_stmt(self, stmt: Any):
        if isinstance(stmt, Assign):
            if isinstance(stmt.target, Signal) and self._is_mux_chain(stmt.value):
                self._emit_mux_chain_as_case(stmt.target.name, stmt.value, 1, "assign")
                return
            rhs = self._emit_expr(stmt.value)
            lhs = self._emit_lhs(stmt.target)
            self.lines.append(f"    assign {lhs} = {rhs};")
        elif isinstance(stmt, IndexedAssign):
            rhs = self._emit_expr(stmt.value)
            self.lines.append(f"    assign {stmt.target_signal.name}[{self._emit_expr(stmt.index)}] = {rhs};")
        elif isinstance(stmt, SubmoduleInst):
            self._emit_submodule_inst(stmt)
        elif isinstance(stmt, IfNode):
            # 顶层 If 只能出现在 generate 块中，暂不常见，直接按 always @(*) 处理
            self._emit_always_comb([stmt])
        elif isinstance(stmt, SwitchNode):
            self._emit_always_comb([stmt])
        elif isinstance(stmt, ForGenNode):
            self.lines.append("    generate")
            self._emit_for_gen(stmt, indent_level=2, mode="assign")
            self.lines.append("    endgenerate")
        elif isinstance(stmt, GenIfNode):
            self.lines.append("    generate")
            self._emit_gen_if(stmt, indent_level=2)
            self.lines.append("    endgenerate")
        elif isinstance(stmt, ArrayWrite):
            rhs = self._emit_expr(stmt.value)
            self.lines.append(f"    assign {stmt.array_name}[{self._emit_expr(stmt.index)}] = {rhs};")
        elif isinstance(stmt, MemWrite):
            # 顶层 memory write 不常见，按 assign 处理
            rhs = self._emit_expr(stmt.value)
            self.lines.append(f"    assign {stmt.mem_name}[{self._emit_expr(stmt.addr)}] = {rhs};")
        elif isinstance(stmt, Comment):
            self._emit_comment(stmt, indent_level=1)
        else:
            raise TypeError(f"Unknown top-level statement: {type(stmt)}")

    def _emit_stmt(self, stmt: Any, indent_level: int, mode: str):
        """mode: 'assign' | 'comb' | 'seq'"""
        prefix = self.indent * indent_level
        if isinstance(stmt, Assign):
            rhs = self._emit_expr(stmt.value)
            lhs = self._emit_lhs(stmt.target)
            if mode == "assign":
                self.lines.append(f"{prefix}assign {lhs} = {rhs};")
            elif mode == "comb":
                self.lines.append(f"{prefix}{lhs} = {rhs};")
            else:  # seq
                self.lines.append(f"{prefix}{lhs} <= {rhs};")
        elif isinstance(stmt, IfNode):
            self.lines.append(f"{prefix}if ({self._emit_expr(stmt.cond)}) begin")
            for s in stmt.then_body:
                self._emit_stmt(s, indent_level + 1, mode)
            if stmt.else_body:
                self.lines.append(f"{prefix}end else begin")
                for s in stmt.else_body:
                    self._emit_stmt(s, indent_level + 1, mode)
                self.lines.append(f"{prefix}end")
            elif mode == "comb":
                # latch guard: always @(*) must have complete assignments
                self.lines.append(f"{prefix}end else begin")
                self.lines.append(f"{prefix}end")
            else:
                self.lines.append(f"{prefix}end")
        elif isinstance(stmt, SwitchNode):
            self.lines.append(f"{prefix}case ({self._emit_expr(stmt.expr)})")
            for val, body in stmt.cases:
                self.lines.append(f"{prefix}{self.indent}{self._emit_expr(val)}: begin")
                for s in body:
                    self._emit_stmt(s, indent_level + 2, mode)
                self.lines.append(f"{prefix}{self.indent}end")
            if stmt.default_body:
                self.lines.append(f"{prefix}{self.indent}default: begin")
                for s in stmt.default_body:
                    self._emit_stmt(s, indent_level + 2, mode)
                self.lines.append(f"{prefix}{self.indent}end")
            elif mode == "comb":
                # latch guard
                self.lines.append(f"{prefix}{self.indent}default: begin")
                self.lines.append(f"{prefix}{self.indent}end")
            self.lines.append(f"{prefix}endcase")
        elif isinstance(stmt, ForGenNode):
            self._emit_for_gen(stmt, indent_level, mode)
        elif isinstance(stmt, GenIfNode):
            self._emit_gen_if(stmt, indent_level)
        elif isinstance(stmt, IndexedAssign):
            if mode == "assign":
                self.lines.append(
                    f"{prefix}assign {stmt.target_signal.name}[{self._emit_expr(stmt.index)}] = {self._emit_expr(stmt.value)};"
                )
            else:
                op = "=" if stmt.blocking else "<="
                self.lines.append(
                    f"{prefix}{stmt.target_signal.name}[{self._emit_expr(stmt.index)}] {op} {self._emit_expr(stmt.value)};"
                )
        elif isinstance(stmt, ArrayWrite):
            op = "<=" if mode == "seq" and not stmt.blocking else "="
            self.lines.append(
                f"{prefix}{stmt.array_name}[{self._emit_expr(stmt.index)}] {op} {self._emit_expr(stmt.value)};"
            )
        elif isinstance(stmt, MemWrite):
            op = "<=" if mode == "seq" else "="
            self.lines.append(
                f"{prefix}{stmt.mem_name}[{self._emit_expr(stmt.addr)}] {op} {self._emit_expr(stmt.value)};"
            )
        elif isinstance(stmt, SubmoduleInst):
            # 在 generate-for 块中支持子模块实例化
            self._emit_submodule_inst_with_indent(stmt, indent_level, mode)
        elif isinstance(stmt, Comment):
            self._emit_comment(stmt, indent_level)
        else:
            raise TypeError(f"Unknown statement: {type(stmt)}")

    def _is_simple_comb_block(self, body: List[Any]) -> bool:
        """判断 comb block 是否仅由 assign / indexed assign / array write / comment 组成。"""
        for stmt in body:
            if not isinstance(stmt, (Assign, IndexedAssign, ArrayWrite, Comment)):
                return False
        return True

    def _emit_simple_comb(self, body: List[Any]):
        """将简单 comb block 输出为 assign 语句（避免 iverilog 中 always @(*) time-0 X 问题）。

        如果 block 中包含级联 Mux（查表模式），则统一输出为 always @(*) case，以提高可读性。
        """
        has_mux_chain = any(
            isinstance(stmt, Assign) and isinstance(stmt.target, Signal) and self._is_mux_chain(stmt.value) for stmt in body
        )
        if has_mux_chain:
            self.lines.append("    always @(*) begin")
            for stmt in body:
                if isinstance(stmt, Assign):
                    if isinstance(stmt.target, Signal) and self._is_mux_chain(stmt.value):
                        self._emit_mux_chain_as_case(stmt.target.name, stmt.value, 2, "comb")
                    else:
                        lhs = self._emit_lhs(stmt.target)
                        self.lines.append(f"        {lhs} = {self._emit_expr(stmt.value)};")
                elif isinstance(stmt, IndexedAssign):
                    self.lines.append(
                        f"        {stmt.target_signal.name}[{self._emit_expr(stmt.index)}] = {self._emit_expr(stmt.value)};"
                    )
                elif isinstance(stmt, ArrayWrite):
                    self.lines.append(
                        f"        {stmt.array_name}[{self._emit_expr(stmt.index)}] = {self._emit_expr(stmt.value)};"
                    )
                elif isinstance(stmt, Comment):
                    self._emit_comment(stmt, indent_level=2)
            self.lines.append("    end")
            self.lines.append("")
            return

        for stmt in body:
            if isinstance(stmt, Assign):
                rhs = self._emit_expr(stmt.value)
                lhs = self._emit_lhs(stmt.target)
                self.lines.append(f"    assign {lhs} = {rhs};")
            elif isinstance(stmt, IndexedAssign):
                rhs = self._emit_expr(stmt.value)
                self.lines.append(
                    f"    assign {stmt.target_signal.name}[{self._emit_expr(stmt.index)}] = {rhs};"
                )
            elif isinstance(stmt, ArrayWrite):
                rhs = self._emit_expr(stmt.value)
                self.lines.append(
                    f"    assign {stmt.array_name}[{self._emit_expr(stmt.index)}] = {rhs};"
                )
            elif isinstance(stmt, Comment):
                self._emit_comment(stmt, indent_level=1)
        if body:
            self.lines.append("")

    def _emit_always_comb(self, body: List[Any]):
        keyword = "always_comb" if self.use_sv_always else "always @(*)"
        self.lines.append(f"    {keyword} begin")
        for stmt in body:
            self._emit_stmt(stmt, 2, "comb")
        self.lines.append("    end")
        self.lines.append("")

    def _emit_always_seq(self, clk: Signal, rst: Optional[Signal], reset_async: bool, reset_active_low: bool, body: List[Any]):
        if rst is not None and reset_async:
            if reset_active_low:
                sens = f"posedge {clk.name} or negedge {rst.name}"
            else:
                sens = f"posedge {clk.name} or posedge {rst.name}"
        else:
            sens = f"posedge {clk.name}"
        keyword = "always_ff" if self.use_sv_always else "always"
        self.lines.append(f"    {keyword} @({sens}) begin")
        for stmt in body:
            self._emit_stmt(stmt, 2, "seq")
        self.lines.append("    end")
        self.lines.append("")

    def _emit_for_gen(self, stmt: Any, indent_level: int, mode: str):
        prefix = self.indent * indent_level
        if mode == "assign":
            # 模块顶层：使用 genvar + generate for
            self.lines.append(f"{prefix}genvar {stmt.var_name};")
            self.lines.append(
                f"{prefix}for ({stmt.var_name} = {stmt.start}; "
                f"{stmt.var_name} < {stmt.end}; "
                f"{stmt.var_name} = {stmt.var_name} + 1) begin : genblk"
            )
        else:
            # always 块内：使用 integer for
            self.lines.append(
                f"{prefix}for (integer {stmt.var_name} = {stmt.start}; "
                f"{stmt.var_name} < {stmt.end}; "
                f"{stmt.var_name} = {stmt.var_name} + 1) begin"
            )
        for s in stmt.body:
            self._emit_stmt(s, indent_level + 1, mode)
        self.lines.append(f"{prefix}end")

    def _emit_gen_if(self, stmt: GenIfNode, indent_level: int):
        prefix = self.indent * indent_level
        self.lines.append(f"{prefix}if ({self._emit_expr(stmt.cond)}) begin : genif")
        for s in stmt.then_body:
            self._emit_stmt(s, indent_level + 1, "assign")
        if stmt.else_body:
            self.lines.append(f"{prefix}end else begin : genelse")
            for s in stmt.else_body:
                self._emit_stmt(s, indent_level + 1, "assign")
        self.lines.append(f"{prefix}end")

    # -----------------------------------------------------------------
    # Submodules
    # -----------------------------------------------------------------
    def _emit_submodule_inst(self, stmt: SubmoduleInst):
        self._emit_submodule_inst_with_indent(stmt, indent_level=1)

    def _emit_submodule_inst_with_indent(self, stmt: SubmoduleInst, indent_level: int, mode: str = "assign"):
        prefix = self.indent * indent_level
        inner = self.indent * (indent_level + 1)
        mod = stmt.module
        type_name = getattr(mod, '_type_name', mod.name)
        id_remap = getattr(self, "_module_id_remap", {})
        mod_name = id_remap.get(id(mod), getattr(self, "_module_name_remap", {}).get(mod.name, type_name))
        params = stmt.params
        if params:
            plist = ", ".join(f".{k}({self._emit_param_override(v)})" for k, v in params.items())
            self.lines.append(f"{prefix}{mod_name} #({plist}) {stmt.name} (")
        else:
            self.lines.append(f"{prefix}{mod_name} {stmt.name} (")

        port_map = stmt.port_map
        items = list(port_map.items())
        for i, (port_name, expr) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            expr_obj = _to_expr(expr) if isinstance(expr, Signal) else expr
            self.lines.append(f"{inner}.{port_name}({self._emit_expr(expr_obj)}){comma}")
        self.lines.append(f"{prefix});")
        self.lines.append("")

    def _emit_implicit_submodule(self, inst_name: str, submod: Module, parent: Module):
        """为 self.sub = Submodule() 这种隐式实例化生成默认端口映射（按名称匹配）以及参数映射。"""
        port_map: Dict[str, Union[Signal, Expr]] = {}
        for pname in list(submod._inputs.keys()) + list(submod._outputs.keys()):
            if hasattr(parent, pname):
                val = getattr(parent, pname)
                if isinstance(val, Signal):
                    port_map[pname] = val

        # 自动参数映射：子模块的参数如果在父模块中有同名属性，则自动传递
        params: Dict[str, Any] = {}
        for pname, param in submod._params.items():
            if hasattr(parent, pname):
                val = getattr(parent, pname)
                if isinstance(val, (Signal, int, str)):
                    params[pname] = val
                elif hasattr(val, "value") and isinstance(getattr(val, "value"), (int, str)):
                    params[pname] = val

        # 合并用户显式绑定的参数表达式（支持跨层级复杂表达式）
        for pname, val in getattr(submod, "_param_bindings", {}).items():
            params[pname] = val

        inst = SubmoduleInst(inst_name, submod, params, port_map)
        self._emit_submodule_inst(inst)

    # -----------------------------------------------------------------
    # Expressions
    # -----------------------------------------------------------------
    # -----------------------------------------------------------------
    # Output reg inference
    # -----------------------------------------------------------------
    def _collect_reg_outputs(self, module: Module) -> set:
        """收集所有在 always 块中被驱动的 Output 信号名。"""
        reg_outputs: set = set()
        for stmt in module._top_level:
            self._scan_stmt_for_reg_outputs(stmt, "top", reg_outputs)
        for body in module._comb_blocks:
            if self._is_simple_comb_block(body):
                continue
            for stmt in body:
                self._scan_stmt_for_reg_outputs(stmt, "comb", reg_outputs)
        for clk, rst, reset_async, reset_active_low, body in module._seq_blocks:
            for stmt in body:
                self._scan_stmt_for_reg_outputs(stmt, "seq", reg_outputs)
        return reg_outputs

    def _scan_stmt_for_reg_outputs(self, stmt: Any, mode: str, reg_outputs: set):
        if isinstance(stmt, Assign):
            if isinstance(stmt.target, Output) and mode in ("comb", "seq"):
                reg_outputs.add(stmt.target.name)
        elif isinstance(stmt, IfNode):
            for s in stmt.then_body:
                self._scan_stmt_for_reg_outputs(s, mode, reg_outputs)
            for s in stmt.else_body:
                self._scan_stmt_for_reg_outputs(s, mode, reg_outputs)
        elif isinstance(stmt, SwitchNode):
            for _, body in stmt.cases:
                for s in body:
                    self._scan_stmt_for_reg_outputs(s, mode, reg_outputs)
            for s in stmt.default_body:
                self._scan_stmt_for_reg_outputs(s, mode, reg_outputs)

    def _emit_comment(self, stmt: Comment, indent_level: int):
        prefix = self.indent * indent_level
        for line in stmt.text.strip().splitlines():
            self.lines.append(f"{prefix}// {line}")

    # -----------------------------------------------------------------
    # Mux chain -> case optimization
    # -----------------------------------------------------------------
    def _is_eq_to_const(self, expr: Expr) -> Optional[tuple]:
        """检测 expr 是否为 (sel == const) 或 (const == sel)，返回 (sel_expr, const_val)。"""
        if isinstance(expr, BinOp) and expr.op == '==':
            if isinstance(expr.lhs, Const):
                return (expr.rhs, int(expr.lhs.value))
            if isinstance(expr.rhs, Const):
                return (expr.lhs, int(expr.rhs.value))
        return None

    def _is_mux_chain(self, expr: Expr) -> bool:
        """检测是否为级联 Mux（查表）模式。"""
        if not isinstance(expr, Mux):
            return False
        eq = self._is_eq_to_const(expr.cond)
        if eq is None:
            return False
        sel_expr, _ = eq
        if isinstance(expr.false_expr, Mux):
            return self._is_mux_chain_with_sel(expr.false_expr, sel_expr)
        return True

    def _is_mux_chain_with_sel(self, expr: Expr, sel_expr: Expr) -> bool:
        if not isinstance(expr, Mux):
            return False
        eq = self._is_eq_to_const(expr.cond)
        if eq is None:
            return False
        cur_sel, _ = eq
        # 简单结构比较：这里只要求 sel 表达式文本相同
        if self._emit_expr(cur_sel) != self._emit_expr(sel_expr):
            return False
        if isinstance(expr.false_expr, Mux):
            return self._is_mux_chain_with_sel(expr.false_expr, sel_expr)
        return True

    def _extract_mux_chain(self, expr: Expr) -> tuple:
        """提取级联 Mux 的 (sel_expr, [(const_val, true_expr), ...], default_expr)。"""
        cases = []
        sel_expr = None
        current = expr
        while isinstance(current, Mux):
            eq = self._is_eq_to_const(current.cond)
            if eq is None:
                break
            cur_sel, const_val = eq
            if sel_expr is None:
                sel_expr = cur_sel
            elif self._emit_expr(cur_sel) != self._emit_expr(sel_expr):
                break
            cases.append((const_val, current.true_expr))
            current = current.false_expr
        return (sel_expr, cases, current)

    def _emit_lhs(self, target) -> str:
        if isinstance(target, Signal):
            return target.name
        return self._emit_expr(target)

    def _emit_mux_chain_as_case(self, target_name: str, expr: Expr, indent_level: int, mode: str):
        """将级联 Mux 输出为 case 语句（可选 always @(*) 包装）。"""
        prefix = self.indent * indent_level
        inner = self.indent * (indent_level + 1)
        sel_expr, cases, default_expr = self._extract_mux_chain(expr)
        op = "=" if mode in ("assign", "comb") else "<="
        wrap_always = mode in ("assign",)
        if wrap_always:
            self.lines.append(f"{prefix}always @(*) begin")
            case_indent = indent_level + 1
        else:
            case_indent = indent_level
        case_prefix = self.indent * case_indent
        item_prefix = self.indent * (case_indent + 1)
        self.lines.append(f"{case_prefix}case ({self._emit_expr(sel_expr)})")
        for const_val, true_expr in cases:
            self.lines.append(f"{item_prefix}{const_val}: {target_name} {op} {self._emit_expr(true_expr)};")
        self.lines.append(f"{item_prefix}default: {target_name} {op} {self._emit_expr(default_expr)};")
        self.lines.append(f"{case_prefix}endcase")
        if wrap_always:
            self.lines.append(f"{prefix}end")

    def _emit_param_override(self, v: Any) -> str:
        """参数覆盖值生成：保持原始数值形式，不附加位宽。"""
        if isinstance(v, int):
            return str(v)
        if isinstance(v, Const):
            return str(int(v.value))
        return self._emit_expr(_to_expr(v))

    def _emit_expr(self, expr: Expr) -> str:
        if isinstance(expr, int):
            width = max(expr.bit_length(), 1)
            return f"{width}'d{expr}"
        if isinstance(expr, Const):
            val = int(expr.value)
            return f"{expr.width}'d{val}"
        if isinstance(expr, Ref):
            return expr.signal.name
        if isinstance(expr, BinOp):
            return f"({self._emit_expr(expr.lhs)} {expr.op} {self._emit_expr(expr.rhs)})"
        if isinstance(expr, UnaryOp):
            return f"({expr.op}{self._emit_expr(expr.operand)})"
        if isinstance(expr, Slice):
            if expr.hi == expr.lo:
                return f"{self._emit_expr(expr.operand)}[{expr.hi}]"
            return f"{self._emit_expr(expr.operand)}[{expr.hi}:{expr.lo}]"
        if isinstance(expr, PartSelect):
            return f"{self._emit_expr(expr.operand)}[{self._emit_expr(expr.offset)} +: {expr.width}]"
        if isinstance(expr, Concat):
            parts = ", ".join(self._emit_expr(op) for op in expr.operands)
            return f"{{{parts}}}"
        if isinstance(expr, Mux):
            return f"({self._emit_expr(expr.cond)} ? {self._emit_expr(expr.true_expr)} : {self._emit_expr(expr.false_expr)})"
        if isinstance(expr, MemRead):
            return f"{expr.mem_name}[{self._emit_expr(expr.addr)}]"
        if isinstance(expr, ArrayRead):
            return f"{expr.array_name}[{self._emit_expr(expr.index)}]"
        if isinstance(expr, BitSelect):
            return f"{self._emit_expr(expr.operand)}[{self._emit_expr(expr.index)}]"
        if isinstance(expr, GenVar):
            return expr.name
        raise TypeError(f"Unknown expression: {type(expr)}")


def _to_expr(val: Any) -> Expr:
    from rtlgen.core import Parameter
    if isinstance(val, Signal):
        return val._expr
    if isinstance(val, Parameter):
        # 参数传递时生成参数名引用，如 .WIDTH(WIDTH)
        s = Signal(width=1, name=val.name)
        return Ref(s)
    if isinstance(val, int):
        width = max(val.bit_length(), 1)
        return Const(value=val, width=width)
    if isinstance(val, Expr):
        return val
    raise TypeError(f"Cannot convert {type(val)} to expression")
