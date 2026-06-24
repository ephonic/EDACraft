"""
rtlgen_x.dsl.codegen — Verilog 代码生成后端

将 rtlgen_x.dsl.core 构建的 AST 与模块层次遍历输出为可综合的 Verilog-2001 代码。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from rtlgen_x.dsl.core import (
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
    FunctionCall,
    GenIfNode,
    GenVar,
    IfNode,
    IndexedAssign,
    LocalParam,
    MemRead,
    MemWrite,
    Memory,
    Module,
    ModuleDoc,
    Mux,
    Output,
    PartSelect,
    Ref,
    Reg,
    Signal,
    SourceLoc,
    Wire,
    Slice,
    SubmoduleInst,
    WhenNode,
    SwitchNode,
    UnaryOp,
)


@dataclass
class EmitProfile:
    """Verilog 发射配置档。"""
    style: str = "review"           # "review" | "default" | "compact" | legacy aliases
    always_comb: bool = False       # 使用 always_comb 而非 always @(*)
    always_ff: bool = False         # 使用 always_ff 而非 always
    explicit_nettype: bool = False  # 在文件头添加 `default_nettype none
    one_module_per_file: bool = False
    reset_style: Optional[str] = None  # None | "async_low" | "async_high" | "sync"
    language: str = "verilog2001"   # "verilog2001" | "systemverilog"
    emit_header: Optional[bool] = None
    emit_port_table: Optional[bool] = None
    emit_block_comments: Optional[bool] = None
    prefer_sv_always: Optional[bool] = None
    disable_cse: Optional[bool] = None
    enable_complexity_extraction: Optional[bool] = None
    explicit_blank_lines: Optional[bool] = None

    @classmethod
    def review(cls, **overrides: Any) -> "EmitProfile":
        return cls(style="review", **overrides)

    @classmethod
    def default(cls, **overrides: Any) -> "EmitProfile":
        return cls(style="default", **overrides)

    @classmethod
    def compact(cls, **overrides: Any) -> "EmitProfile":
        return cls(style="compact", **overrides)

    @classmethod
    def systemverilog(cls, style: str = "review", **overrides: Any) -> "EmitProfile":
        return cls(
            style=style,
            language="systemverilog",
            always_comb=True,
            always_ff=True,
            **overrides,
        )

    def resolved(self) -> Dict[str, Any]:
        raw_style = (self.style or "review").lower()
        style = raw_style
        if style in ("simple", "review", "lowrisc", "synopsys"):
            style = "review"
        elif style in ("sv", "default"):
            style = "default"
        elif style == "compact":
            style = "compact"

        config: Dict[str, Any] = {
            "style": style,
            "always_comb": self.always_comb,
            "always_ff": self.always_ff,
            "explicit_nettype": self.explicit_nettype,
            "one_module_per_file": self.one_module_per_file,
            "reset_style": self.reset_style,
            "language": self.language,
            "emit_header": style != "compact",
            "emit_port_table": style != "compact",
            "emit_block_comments": style != "compact",
            "prefer_sv_always": self.language == "systemverilog" or raw_style == "sv",
            "disable_cse": style != "compact",
            "enable_complexity_extraction": style != "compact",
            "explicit_blank_lines": style != "compact",
        }

        overrides = {
            "emit_header": self.emit_header,
            "emit_port_table": self.emit_port_table,
            "emit_block_comments": self.emit_block_comments,
            "prefer_sv_always": self.prefer_sv_always,
            "disable_cse": self.disable_cse,
            "enable_complexity_extraction": self.enable_complexity_extraction,
            "explicit_blank_lines": self.explicit_blank_lines,
        }
        for key, value in overrides.items():
            if value is not None:
                config[key] = value

        if self.always_comb:
            config["prefer_sv_always"] = True
        return config


class VerilogEmitter:
    """Verilog 代码发射器。"""

    def __init__(self, indent: str = "    ", use_sv_always: bool = False, emit_source_map: bool = False, profile: Optional[EmitProfile] = None, disable_cse: bool = True):
        self.indent = indent
        self.use_sv_always = use_sv_always
        self.emit_source_map = emit_source_map
        self.profile = profile
        self.disable_cse = disable_cse
        self.lines: List[str] = []
        self._cse_counter: int = 0  # global CSE wire counter across all always blocks
        self._emit_header = True
        self._emit_port_table = True
        self._emit_block_comments = True
        self._enable_complexity_extraction = True
        self._explicit_blank_lines = True

        # Apply profile overrides
        if profile is not None:
            resolved = profile.resolved()
            self._emit_header = resolved["emit_header"]
            self._emit_port_table = resolved["emit_port_table"]
            self._emit_block_comments = resolved["emit_block_comments"]
            self._enable_complexity_extraction = resolved["enable_complexity_extraction"]
            self._explicit_blank_lines = resolved["explicit_blank_lines"]
            self.disable_cse = resolved["disable_cse"]
            if resolved["prefer_sv_always"]:
                self.use_sv_always = True

    def _append_blank_line(self) -> None:
        if self._explicit_blank_lines:
            self.lines.append("")

    def _emit_section_comment(self, title: str) -> None:
        if self._emit_block_comments:
            self.lines.append(f"    // {title}")

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------
    def emit(self, module: Module) -> str:
        """生成单个模块的 Verilog 代码。"""
        self._validate_storage_codegen_subset(module)
        self.lines = []
        self._extra_port_wires: List[Tuple[str, str]] = []
        self._port_expr_names: set[str] = set()
        self._port_expr_map: Dict[Tuple[str, str], str] = {}
        self._memory_decl_map: Dict[str, Any] = {}
        # Build mapping from submodule port signal id to instance name.
        # This lets us emit prefixed names (e.g. u_valu_wid) when a submodule
        # port is referenced directly, avoiding name collisions between different
        # submodule instances that have ports with the same bare name.
        self._submod_port_inst_map: Dict[int, str] = {}
        def _collect_submods(body):
            for stmt in body:
                if isinstance(stmt, SubmoduleInst):
                    for sig in list(stmt.module._inputs.values()) + list(stmt.module._outputs.values()):
                        self._submod_port_inst_map[id(sig)] = stmt.name
                elif hasattr(stmt, 'then_body'):
                    _collect_submods(stmt.then_body)
                    if hasattr(stmt, 'else_body'):
                        _collect_submods(stmt.else_body)
        for inst_name, submod in module._submodules:
            for sig in list(submod._inputs.values()) + list(submod._outputs.values()):
                self._submod_port_inst_map[id(sig)] = inst_name
        _collect_submods(module._top_level)
        for body in module._comb_blocks:
            _collect_submods(body)
        for _, _, _, _, body in module._seq_blocks:
            _collect_submods(body)
        self._emit_module(module)
        del self._memory_decl_map
        del self._submod_port_inst_map
        return "\n".join(self.lines)

    def _validate_storage_codegen_subset(self, module: Module) -> None:
        for memory in getattr(module, "_memories", {}).values():
            read_style = getattr(memory, "read_style", "async")
            read_latency = int(getattr(memory, "read_latency", 0))
            if read_style == "sync" or read_latency != 0:
                raise NotImplementedError(
                    "VerilogEmitter does not yet synthesize explicit sync-read/read-latency memories; "
                    "use the executable lowering path for simulation, or author explicit sampled-output RTL"
                )

    def emit_with_lint(self, module: Module, auto_fix: bool = False, rules: Optional[List[str]] = None) -> Tuple[str, "LintResult"]:
        """生成 Verilog 并运行 lint，返回 (verilog_text, lint_result)。"""
        from rtlgen_x.dsl.lint import VerilogLinter
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
        visited: set = set()
        order: List[Module] = []

        def _dfs_stmts(stmts: List[Any]):
            for stmt in stmts:
                if isinstance(stmt, SubmoduleInst):
                    dfs(stmt.module)
                elif isinstance(stmt, IfNode):
                    _dfs_stmts(stmt.then_body)
                    for _, body in stmt.elif_bodies:
                        _dfs_stmts(body)
                    _dfs_stmts(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, body in stmt.cases:
                        _dfs_stmts(body)
                    _dfs_stmts(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    _dfs_stmts(stmt.body)
                elif isinstance(stmt, GenIfNode):
                    _dfs_stmts(stmt.then_body)
                    for _, body in stmt.elif_bodies:
                        _dfs_stmts(body)
                    _dfs_stmts(stmt.else_body)
                elif isinstance(stmt, WhenNode):
                    for _, body in stmt.branches:
                        _dfs_stmts(body)

        def dfs(mod: Module):
            if id(mod) in visited:
                return
            visited.add(id(mod))
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
        used_names: set = set()
        for mod in order:
            fp = _fingerprint(mod)
            if fp in fingerprint_to_canonical:
                canonical = fingerprint_to_canonical[fp]
                canonical_name = self._preferred_sv_module_name(canonical)
                name_remap[mod.name] = canonical_name
                id_remap[id(mod)] = canonical_name
            else:
                fingerprint_to_canonical[fp] = mod
                base_name = self._preferred_sv_module_name(mod)
                unique_name = base_name
                suffix = 1
                while unique_name in used_names:
                    unique_name = f"{base_name}_{suffix}"
                    suffix += 1
                used_names.add(unique_name)
                name_remap[mod.name] = unique_name
                id_remap[id(mod)] = unique_name
                deduped_order.append(mod)

        self._module_name_remap = name_remap
        self._module_id_remap = id_remap
        try:
            parts = []
            for mod in deduped_order:
                parts.append(self.emit(mod))
                parts.append("")
            if include_assertions:
                from rtlgen_x.dsl.svagen import SVAEmitter
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

    def emit_design_with_source_map(self, top_module: Module) -> Tuple[str, dict]:
        """生成整个设计的 Verilog 代码和源码映射表。

        返回 ``(verilog_text, source_map)``，其中 source_map 将
        Verilog 行号映射回 Python 源文件位置。
        """
        old_source_map = self.emit_source_map
        self.emit_source_map = True
        try:
            verilog_text = self.emit_design(top_module)
            source_map: dict = {}
            for i, line in enumerate(verilog_text.split("\n"), 1):
                stripped = line.strip()
                if stripped.startswith("// rtlcraft: source="):
                    # 记录源码位置供后续查找
                    src_info = stripped[len("// rtlcraft: source="):]
                    source_map[i] = src_info
            return verilog_text, source_map
        finally:
            self.emit_source_map = old_source_map

    def _preferred_sv_module_name(self, module: Module) -> str:
        """Return the user-authored HDL name for a module."""
        return getattr(module, "name", None) or getattr(module, "_type_name", "module")

    def _emitted_sv_module_name(self, module: Module) -> str:
        """Return the actual emitted HDL declaration name for a module."""
        id_remap = getattr(self, "_module_id_remap", {})
        if id(module) in id_remap:
            return id_remap[id(module)]
        preferred = self._preferred_sv_module_name(module)
        return getattr(self, "_module_name_remap", {}).get(preferred, preferred)

    # -----------------------------------------------------------------
    # Module header emission (from ModuleDoc)
    # -----------------------------------------------------------------
    def _emit_module_header(self, module: Module):
        """Emit a rich file header with module documentation.

        Generates a structured Verilog comment block containing:
        - File info (module name, source, author, version)
        - Description of functionality
        - Port information table
        - Timing/protocol notes
        - Per-always-block descriptions (if provided in ModuleDoc)
        """
        if not self._emit_header:
            return
        doc = getattr(module, '_module_doc', None)
        if doc is None:
            # Fallback: emit minimal header with module name
            self.lines.append(f"// ==========================================================")
            self.lines.append(f"// Module: {self._emitted_sv_module_name(module)}")
            self.lines.append(f"// ==========================================================")
            self._append_blank_line()
            return

        mod_name = self._emitted_sv_module_name(module)
        sep = "// " + "=" * 56

        self.lines.append(sep)
        self.lines.append(f"// Module       : {mod_name}")
        if doc.source:
            self.lines.append(f"// Source        : {doc.source}")
        if doc.author:
            self.lines.append(f"// Author        : {doc.author}")
        if doc.version:
            self.lines.append(f"// Version       : {doc.version}")
        self.lines.append(f"// Description   : {doc.description}")
        self.lines.append(sep)

        # Port information table
        self._emit_port_table(module)

        # Timing/protocol notes
        if doc.timing:
            self.lines.append("//")
            self.lines.append("// Timing / Protocol:")
            self.lines.append(f"//   {doc.timing}")
            self.lines.append("//")

        # Additional port description
        if doc.port_description:
            self.lines.append("//")
            for line in doc.port_description.splitlines():
                self.lines.append(f"//   {line}")
            self.lines.append("//")

        self._append_blank_line()

    def _emit_port_table(self, module: Module):
        """Emit a formatted table of input and output ports."""
        if not self._emit_port_table:
            return
        inputs = list(module._inputs.values())
        outputs = list(module._outputs.values())

        if not inputs and not outputs:
            return

        self.lines.append("//")
        self.lines.append("// Ports:")
        self.lines.append("//   Direction | Width | Name")
        self.lines.append("//   " + "-" * 36)

        for sig in inputs:
            w = str(sig.width) if sig.width > 1 else "1"
            self.lines.append(f"//   {'input':<10}| {w:>5} | {sig.name}")
        for sig in outputs:
            w = str(sig.width) if sig.width > 1 else "1"
            self.lines.append(f"//   {'output':<10}| {w:>5} | {sig.name}")
        self.lines.append("//")

    # -----------------------------------------------------------------
    # Module emission
    # -----------------------------------------------------------------
    def _emit_module(self, module: Module):
        # `default_nettype none` — 防止隐式 wire 推断
        if self.profile is not None and self.profile.explicit_nettype:
            self.lines.append("`default_nettype none")
            self._append_blank_line()

        # ---- File header from ModuleDoc (agent-injected documentation) ----
        self._emit_module_header(module)

        # 模块级注释与建议
        if self._emit_block_comments and (module._module_comments or module._module_suggestions):
            for line in module._module_comments:
                self.lines.append(f"// {line}")
            if module._module_suggestions:
                self.lines.append("// PPA Suggestions:")
                for sug in module._module_suggestions:
                    self.lines.append(f"//   - {sug}")
            self._append_blank_line()

        # 先推导哪些 Output 需要在 always 块中被驱动，从而声明为 output reg
        reg_outputs = self._collect_reg_outputs(module)

        # 参数声明：区分可配置的 parameter 和局部的 localparam
        params = list(module._params.values())
        module_params = [p for p in params if not isinstance(p, LocalParam)]
        mod_name = self._emitted_sv_module_name(module)
        if module_params:
            def _fmt_param_val(v):
                if isinstance(v, str):
                    return f'"{v}"'
                return str(v)
            param_lines = ", ".join(f"parameter {p.name} = {_fmt_param_val(p.value)}" for p in module_params)
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
        self._append_blank_line()

        # Memory 声明
        has_memory_section = bool(module._memories or module._arrays)
        if has_memory_section:
            self._emit_section_comment("Storage declarations")
        self._emit_memory_decls(module)

        # 内部信号声明
        if (
            module._params
            or module._wires
            or module._regs
            or module._arrays
        ):
            self._emit_section_comment("Internal declarations")
        self._emit_internal_decls(module)

        # Audit Fix 0522 — Section 2.2: Resolve cross-module assignments
        # (e.g., ifu.clk <<= self.clk) into proper submodule port connections
        # instead of redundant "assign clk = clk;" statements.
        self._resolve_cross_module_assignments(module)

        # Pre-collect helper wires so review output can present them before
        # the instance list that consumes them.
        self._collect_structural_port_helpers(module)

        # 顶层语句（assign、子模块实例等）
        if module._top_level or module._submodules:
            self._emit_section_comment("Structural wiring and instances")

        # Helper wires for complex submodule port expressions live with structural wiring.
        if self._extra_port_wires:
            self.lines.append("    // Port connection helpers")
            for decl_line, assign_line in self._extra_port_wires:
                self.lines.append(decl_line)
                self.lines.append(assign_line)
            self._append_blank_line()

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

        # 锁存器块 (always_latch)
        if module._latch_blocks:
            self._emit_section_comment("Latch logic")
        for body in module._latch_blocks:
            self._emit_always_latch(body)

        # 初始化块 (initial)
        if module._init_blocks:
            self._emit_section_comment("Initialization")
        for body in module._init_blocks:
            self._emit_initial(body)

        # 组合逻辑块
        if module._comb_blocks:
            self._emit_section_comment("Combinational logic")
        doc = getattr(module, '_module_doc', None)
        comb_docs = list(doc.always_descriptions) if doc else []
        comb_idx = 0
        for body in module._comb_blocks:
            doc_comment = ""
            if self._emit_block_comments:
                if comb_idx < len(comb_docs) and comb_docs[comb_idx][0] == "Comb":
                    doc_comment = comb_docs[comb_idx][1]
                    comb_idx += 1
                if not doc_comment:
                    # Auto-generate comment from assigned targets
                    doc_comment = self._auto_always_comment(body, "Comb")
            if self._is_simple_comb_block(body):
                self._emit_simple_comb(body, doc_comment=doc_comment)
            else:
                self._emit_always_comb(body, doc_comment=doc_comment)

        # 时序逻辑块
        if module._seq_blocks:
            self._emit_section_comment("Sequential logic")
        seq_docs = list(doc.always_descriptions) if doc else []
        seq_idx = 0
        # Skip already-used Comb entries
        for _ in seq_docs[:]:
            if _[0] == "Comb":
                seq_idx += 1
            else:
                break
        for clk, rst, reset_async, reset_active_low, body in module._seq_blocks:
            doc_comment = ""
            if self._emit_block_comments:
                if seq_idx < len(seq_docs) and seq_docs[seq_idx][0] in ("Seq", "Reset"):
                    doc_comment = seq_docs[seq_idx][1]
                    seq_idx += 1
                if not doc_comment:
                    doc_comment = self._auto_always_comment(body, "Seq")
            self._emit_always_seq(clk, rst, reset_async, reset_active_low, body, doc_comment=doc_comment)

        self.lines.append("endmodule")

    def _port_decl(self, direction: str, sig: Signal, reg_outputs: set) -> str:
        is_reg = sig.name in reg_outputs
        reg_str = " reg" if is_reg else ""
        if sig.width == 1:
            return f"{direction}{reg_str} {sig.name}"
        return f"{direction}{reg_str} [{sig.width - 1}:0] {sig.name}"

    def _emit_memory_decls(self, module: Module):
        seen: set = set()
        # Collect arrays from explicit registry AND auto-discover from AST
        # Start with already-registered arrays/memories so auto-discovery doesn't override
        all_arrays: Dict[str, Any] = dict(module._memories)
        all_arrays.update(module._arrays)
        self._collect_arrays_from_ast(module, all_arrays)
        self._memory_decl_map = dict(all_arrays)
        registered_array_names = {a.name for a in module._arrays.values()}
        for mem in all_arrays.values():
            if mem.name in seen:
                continue
            # Skip arrays already registered in module._arrays — they're emitted in _emit_internal_decls
            if mem.name in registered_array_names:
                continue
            seen.add(mem.name)
            self.lines.append(f"    reg [{mem.width - 1}:0] {mem.name} [0:{mem.depth - 1}];")
            if getattr(mem, 'init_file', None):
                self.lines.append(f"    initial begin")
                self.lines.append(f"        $readmemh(\"{mem.init_file}\", {mem.name});")
                self.lines.append(f"    end")
            elif getattr(mem, 'init_data', None):
                self.lines.append(f"    initial begin")
                for idx, val in enumerate(mem.init_data):
                    literal = self._emit_const_literal(int(val), mem.width)
                    self.lines.append(f"        {mem.name}[{idx}] = {literal};")
                self.lines.append(f"    end")
            elif getattr(mem, 'init_zero', None):
                self.lines.append(f"    initial begin")
                self.lines.append(f"        integer __i;")
                self.lines.append(f"        for (__i = 0; __i < {mem.depth}; __i = __i + 1) begin")
                self.lines.append(f"            {mem.name}[__i] = {mem.width}'d0;")
                self.lines.append(f"        end")
                self.lines.append(f"    end")
        if module._memories:
            self._append_blank_line()

    @staticmethod
    def _extract_literal_int(expr) -> int | None:
        """Extract a literal integer value from an expression node, or None."""
        from rtlgen_x.dsl.core import Const
        if isinstance(expr, Const):
            return expr.value
        if isinstance(expr, int):
            return expr
        return None

    @staticmethod
    def _expr_bit_width(expr) -> int:
        """Estimate the bit-width of an expression node."""
        from rtlgen_x.dsl.core import Const, Slice, Ref
        if isinstance(expr, Const):
            return expr.width
        if isinstance(expr, Slice):
            return expr.hi - expr.lo + 1
        if isinstance(expr, Ref):
            return getattr(expr, 'width', 0)
        return 0

    def _collect_arrays_from_ast(self, module: Module, arrays: Dict[str, Any]):
        """Scan AST for ArrayRead/ArrayWrite and register untracked Array objects."""
        from rtlgen_x.dsl.core import Array, ArrayRead, ArrayWrite

        # Two-pass: first collect all indices, then register with correct depth
        array_indices: Dict[str, set] = {}
        array_widths: Dict[str, int] = {}

        def _record_index(array_name: str, idx_expr, width: int):
            array_widths.setdefault(array_name, width)
            idx_set = array_indices.setdefault(array_name, set())
            # Extract literal integer index
            lit = self._extract_literal_int(idx_expr)
            if lit is not None:
                idx_set.add(lit)
            else:
                # Dynamic index: estimate max from bit-width of the expression
                bw = self._expr_bit_width(idx_expr)
                if bw > 0:
                    idx_set.add((1 << bw) - 1)  # max possible value for bw bits

        def _scan_body(body):
            from rtlgen_x.dsl.core import SwitchNode
            for stmt in body:
                if isinstance(stmt, ArrayWrite):
                    _record_index(stmt.array_name, stmt.index, getattr(stmt, 'width', 64))
                elif isinstance(stmt, ArrayRead):
                    _record_index(stmt.array_name, stmt.index, stmt.width)
                elif hasattr(stmt, 'value'):
                    _scan_expr(stmt.value)
                if hasattr(stmt, 'then_body'):
                    _scan_body(stmt.then_body)
                    if hasattr(stmt, 'else_body'):
                        _scan_body(stmt.else_body)
                if isinstance(stmt, SwitchNode):
                    for _, case_body in stmt.cases:
                        _scan_body(case_body)
                    _scan_body(stmt.default_body)

        def _scan_expr(expr):
            if isinstance(expr, ArrayRead):
                _record_index(expr.array_name, expr.index, expr.width)
            elif hasattr(expr, 'lhs'):
                _scan_expr(expr.lhs)
            if hasattr(expr, 'rhs'):
                _scan_expr(expr.rhs)
            if hasattr(expr, 'operand'):
                _scan_expr(expr.operand)
            if hasattr(expr, 'cond'):
                _scan_expr(expr.cond)
            if hasattr(expr, 'true_expr'):
                _scan_expr(expr.true_expr)
            if hasattr(expr, 'false_expr'):
                _scan_expr(expr.false_expr)
            if hasattr(expr, 'operands'):
                for op in expr.operands:
                    _scan_expr(op)

        for body in module._comb_blocks:
            _scan_body(body)
        for _, _, _, _, body in module._seq_blocks:
            _scan_body(body)
        for stmt in module._top_level:
            _scan_body([stmt])

        # Register arrays with inferred depth from collected indices
        for name, indices in array_indices.items():
            if name not in arrays:
                width = array_widths.get(name, 64)
                max_idx = max(indices) if indices else 0
                depth = max_idx + 1
                arrays[name] = Array(width, depth, name)

    def _collect_undeclared_signals(self, module: Module) -> List[Signal]:
        declared = set()
        for sig in list(module._inputs.values()) + list(module._outputs.values()) + list(module._wires.values()) + list(module._regs.values()):
            declared.add(sig.name)
        for arr in module._arrays.values():
            declared.add(arr.name)
        for _, sub in module._submodules:
            for sig in list(sub._outputs.values()):
                declared.add(sig.name)
        # Exclude Parameter and LocalParam references from undeclared signals
        for p in module._params.values():
            declared.add(p.name)
        
        refs = set()
        def _scan_expr(expr):
            if expr is None:
                return
            if isinstance(expr, Ref):
                refs.add(expr.signal)
            elif isinstance(expr, BinOp):
                _scan_expr(expr.lhs)
                _scan_expr(expr.rhs)
            elif isinstance(expr, Mux):
                _scan_expr(expr.cond)
                _scan_expr(expr.true_expr)
                _scan_expr(expr.false_expr)
            elif isinstance(expr, UnaryOp):
                _scan_expr(expr.operand)
            elif isinstance(expr, Slice):
                _scan_expr(expr.operand)
            elif isinstance(expr, BitSelect):
                _scan_expr(expr.operand)
                _scan_expr(expr.index)
            elif isinstance(expr, PartSelect):
                _scan_expr(expr.operand)
                _scan_expr(expr.offset)
            elif isinstance(expr, Concat):
                for op in expr.operands:
                    _scan_expr(op)
            elif isinstance(expr, (MemRead, ArrayRead)):
                _scan_expr(expr.addr if hasattr(expr, 'addr') else expr.index)
            elif isinstance(expr, FunctionCall):
                for arg in expr.args:
                    _scan_expr(arg)
            elif isinstance(expr, (Const, GenVar, int)):
                pass
        
        def _scan_stmt(stmt):
            if isinstance(stmt, Assign):
                if isinstance(stmt.target, Signal):
                    refs.add(stmt.target)
                _scan_expr(stmt.value)
            elif isinstance(stmt, IndexedAssign):
                _scan_expr(stmt.index)
                _scan_expr(stmt.value)
            elif isinstance(stmt, IfNode):
                _scan_expr(stmt.cond)
                for s in stmt.then_body:
                    _scan_stmt(s)
                for cond, body in stmt.elif_bodies:
                    _scan_expr(cond)
                    for s in body:
                        _scan_stmt(s)
                for s in stmt.else_body:
                    _scan_stmt(s)
            elif isinstance(stmt, WhenNode):
                for cond, body in stmt.branches:
                    if cond is not None:
                        _scan_expr(cond)
                    for s in body:
                        _scan_stmt(s)
            elif isinstance(stmt, SwitchNode):
                _scan_expr(stmt.expr)
                for _, body in stmt.cases:
                    for s in body:
                        _scan_stmt(s)
                for s in stmt.default_body:
                    _scan_stmt(s)
            elif isinstance(stmt, (ArrayWrite, MemWrite)):
                _scan_expr(stmt.index if hasattr(stmt, 'index') else stmt.addr)
                _scan_expr(stmt.value)
            elif isinstance(stmt, SubmoduleInst):
                for expr in stmt.port_map.values():
                    _scan_expr(_to_expr(expr))
            elif isinstance(stmt, ForGenNode):
                for s in stmt.body:
                    _scan_stmt(s)
            elif isinstance(stmt, GenIfNode):
                for s in stmt.then_body:
                    _scan_stmt(s)
                for s in stmt.else_body:
                    _scan_stmt(s)
            elif isinstance(stmt, Comment):
                pass
        
        for stmt in module._top_level:
            _scan_stmt(stmt)
        for body in module._comb_blocks:
            for stmt in body:
                _scan_stmt(stmt)
        for clk, rst, reset_async, reset_active_low, body in module._seq_blocks:
            for stmt in body:
                _scan_stmt(stmt)
        
        undeclared = []
        seen_ids = set()
        for sig in refs:
            if sig.name not in declared and getattr(sig, '_array_parent', None) is None and id(sig) not in seen_ids:
                seen_ids.add(id(sig))
                undeclared.append(sig)
        undeclared.sort(key=lambda s: self._prefixed_name(s))
        return undeclared

    def _emit_internal_decls(self, module: Module):
        # localparam 声明
        localparams = [p for p in module._params.values() if isinstance(p, LocalParam)]
        for p in localparams:
            self.lines.append(f"    localparam {p.name} = {p.value};")
        if localparams:
            self._append_blank_line()

        # 隐式声明
        undeclared = self._collect_undeclared_signals(module)
        seen_names = set()
        for sig in undeclared:
            decl_name = self._prefixed_name(sig)
            if decl_name in seen_names:
                continue
            seen_names.add(decl_name)
            self.lines.append(self._sig_decl("logic", sig, name_override=decl_name))
        if undeclared:
            self._append_blank_line()

        # internal signals (use logic so they can be driven in both assign and always)
        for sig in self._ordered_unique_signals(module._wires.values()):
            # Skip signals that belong to an Array (declared as 2D array below)
            if getattr(sig, '_array_parent', None) is None:
                self.lines.append(self._sig_decl("logic", sig))
        # regs
        for sig in self._ordered_unique_signals(module._regs.values()):
            if getattr(sig, '_array_parent', None) is None:
                self.lines.append(self._sig_decl("reg", sig))
        # arrays
        for arr in module._arrays.values():
            vtype = "reg" if arr._vtype is Reg else "logic"
            if arr.width == 1:
                self.lines.append(f"    {vtype} {arr.name} [0:{arr.depth - 1}];")
            else:
                self.lines.append(f"    {vtype} [{arr.width - 1}:0] {arr.name} [0:{arr.depth - 1}];")
        # Declare wires for unconnected submodule outputs so they can be referenced
        # in parent expressions (e.g. self.valid_out <<= ifu.valid_out | ...)
        declared_names = set()
        for sig in list(module._inputs.values()) + list(module._outputs.values()) + list(module._wires.values()) + list(module._regs.values()):
            declared_names.add(sig.name)
        for arr in module._arrays.values():
            declared_names.add(arr.name)
        for _, sub in module._submodules:
            for sig in sub._outputs.values():
                declared_names.add(sig.name)
        for stmt in module._top_level:
            if isinstance(stmt, SubmoduleInst):
                for port_name, sig in stmt.module._outputs.items():
                    if port_name not in stmt.port_map:
                        wire_name = f"{stmt.name}_{port_name}"
                        if wire_name not in seen_names and wire_name not in declared_names:
                            seen_names.add(wire_name)
                            self.lines.append(self._sig_decl("wire", sig, name_override=wire_name))
        for _, sub in module._submodules:
            for sig in sub._outputs.values():
                if sig.name not in module._wires and sig.name not in module._regs:
                    pass  # implicit signals handled elsewhere or expected to exist
        if module._wires or module._regs or module._arrays or undeclared:
            self._append_blank_line()

    @staticmethod
    def _ordered_unique_signals(signals):
        seen = set()
        ordered = []
        for sig in signals:
            key = id(sig)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(sig)
        return ordered

    def _sig_decl(self, vtype: str, sig: Signal, name_override: Optional[str] = None) -> str:
        init_part = ""
        if isinstance(sig, Reg) and getattr(sig, 'init_value', None) is not None:
            init_part = f" = {self._emit_const_literal(sig.init_value, sig.width)}"
        name = name_override if name_override is not None else sig.name
        if sig.width == 1:
            return f"    {vtype} {name}{init_part};"
        return f"    {vtype} [{sig.width - 1}:0] {name}{init_part};"

    def _stable_port_expr_wire_name(self, inst_name: str, port_name: str) -> str:
        base = f"{inst_name}_{port_name}_expr"
        candidate = base
        suffix = 1
        while candidate in self._port_expr_names:
            suffix += 1
            candidate = f"{base}_{suffix}"
        self._port_expr_names.add(candidate)
        return candidate

    @staticmethod
    def _submodule_port_expr_needs_helper(expr: Expr) -> bool:
        if isinstance(expr, (Slice, PartSelect)):
            op = expr.operand
            if isinstance(op, (Concat, BinOp)):
                return True
        return False

    def _append_port_expr_helper(self, inst_name: str, port_name: str, expr_obj: Expr) -> None:
        key = (inst_name, port_name)
        wire_name = self._port_expr_map.get(key)
        if wire_name is None:
            wire_name = self._stable_port_expr_wire_name(inst_name, port_name)
            self._port_expr_map[key] = wire_name
        helper_decl = f"    wire [{expr_obj.width-1}:0] {wire_name};"
        helper_assign = f"    assign {wire_name} = {self._emit_expr(expr_obj)};"
        pair = (helper_decl, helper_assign)
        if pair not in self._extra_port_wires:
            self._extra_port_wires.append(pair)

    def _collect_submodule_port_helpers(self, stmt: SubmoduleInst) -> None:
        for port_name, expr in stmt.port_map.items():
            if expr is None:
                continue
            expr_obj = _to_expr(expr) if isinstance(expr, Signal) else expr
            if self._submodule_port_expr_needs_helper(expr_obj):
                self._append_port_expr_helper(stmt.name, port_name, expr_obj)

    def _collect_structural_port_helpers(self, module: Module) -> None:
        for stmt in module._top_level:
            if isinstance(stmt, SubmoduleInst):
                self._collect_submodule_port_helpers(stmt)

    # -----------------------------------------------------------------
    # Statements
    # -----------------------------------------------------------------
    def _emit_const_literal(self, val: int, width: int) -> str:
        """Emit a constant literal, handling negative values as unsigned."""
        if val < 0:
            val = val & ((1 << width) - 1)
            return f"{width}'h{val:x}"
        return f"{width}'d{val}"

    def _emit_assign_rhs(self, expr: Expr, target) -> str:
        if isinstance(target, Signal) and isinstance(expr, Const):
            if expr.width < target.width:
                return self._emit_const_literal(int(expr.value), target.width)
        return self._emit_expr(expr)

    def _emit_source_loc(self, stmt: Any, indent_level: int):
        """如果语句带有源码位置且启用了 source map，则发射注释。"""
        if not self.emit_source_map:
            return
        loc = getattr(stmt, "source_location", None)
        if loc is not None:
            prefix = self.indent * indent_level
            fname = loc.file.split("/")[-1] if loc.file else "?"
            self.lines.append(f"{prefix}// rtlcraft: source={fname}:{loc.line}")

    def _emit_toplevel_stmt(self, stmt: Any):
        if isinstance(stmt, Assign):
            self._emit_source_loc(stmt, 1)
            if isinstance(stmt.target, Signal) and self._is_mux_chain(stmt.value):
                self._emit_mux_chain_as_case(stmt.target.name, stmt.value, 1, "assign")
                return
            rhs = self._emit_assign_rhs(stmt.value, stmt.target)
            lhs = self._emit_lhs(stmt.target)
            self.lines.append(f"    assign {lhs} = {rhs};")
        elif isinstance(stmt, IndexedAssign):
            rhs = self._emit_expr(stmt.value)
            tname = self._prefixed_name(stmt.target_signal)
            if stmt.target_signal.width == 1:
                self.lines.append(f"    assign {tname} = {rhs};")
            else:
                self.lines.append(f"    assign {tname}[{self._emit_expr(stmt.index)}] = {rhs};")
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
        elif isinstance(stmt, WhenNode):
            # 顶层 When/Otherwise，按 always @(*) 处理
            self._emit_always_comb([stmt])
        elif isinstance(stmt, Comment):
            self._emit_comment(stmt, indent_level=1)
        else:
            raise TypeError(f"Unknown top-level statement: {type(stmt)}")

    def _emit_stmt(self, stmt: Any, indent_level: int, mode: str):
        """mode: 'assign' | 'comb' | 'seq'"""
        self._emit_source_loc(stmt, indent_level)
        prefix = self.indent * indent_level
        if isinstance(stmt, Assign):
            rhs = self._emit_assign_rhs(stmt.value, stmt.target)
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
            self._emit_else_chain(stmt, indent_level, mode)
        elif isinstance(stmt, WhenNode):
            self._emit_when(stmt, indent_level, mode)
        elif isinstance(stmt, SwitchNode):
            self.lines.append(f"{prefix}{stmt.kind} ({self._emit_expr(stmt.expr)})")
            for val, body in stmt.cases:
                self.lines.append(f"{prefix}{self.indent}{self._emit_case_label(val, stmt.expr.width)}: begin")
                for s in body:
                    self._emit_stmt(s, indent_level + 2, mode)
                self.lines.append(f"{prefix}{self.indent}end")
            if stmt.default_body:
                self.lines.append(f"{prefix}{self.indent}default: begin")
                for s in stmt.default_body:
                    self._emit_stmt(s, indent_level + 2, mode)
                self.lines.append(f"{prefix}{self.indent}end")
            self.lines.append(f"{prefix}endcase")
        elif isinstance(stmt, ForGenNode):
            self._emit_for_gen(stmt, indent_level, mode)
        elif isinstance(stmt, GenIfNode):
            self._emit_gen_if(stmt, indent_level)
        elif isinstance(stmt, IndexedAssign):
            tname = self._prefixed_name(stmt.target_signal)
            if stmt.target_signal.width == 1:
                if mode == "assign":
                    self.lines.append(f"{prefix}assign {tname} = {self._emit_expr(stmt.value)};")
                else:
                    op = "=" if stmt.blocking else "<="
                    self.lines.append(f"{prefix}{tname} {op} {self._emit_expr(stmt.value)};")
            else:
                if mode == "assign":
                    self.lines.append(
                        f"{prefix}assign {tname}[{self._emit_expr(stmt.index)}] = {self._emit_expr(stmt.value)};"
                    )
                else:
                    op = "=" if stmt.blocking else "<="
                    self.lines.append(
                        f"{prefix}{tname}[{self._emit_expr(stmt.index)}] {op} {self._emit_expr(stmt.value)};"
                    )
        elif isinstance(stmt, ArrayWrite):
            op = "<=" if mode == "seq" and not stmt.blocking else "="
            self.lines.append(
                f"{prefix}{stmt.array_name}[{self._emit_expr(stmt.index)}] {op} {self._emit_expr(stmt.value)};"
            )
        elif isinstance(stmt, MemWrite):
            self._emit_mem_write(stmt, indent_level, mode)
        elif isinstance(stmt, SubmoduleInst):
            # 在 generate-for 块中支持子模块实例化
            self._emit_submodule_inst_with_indent(stmt, indent_level, mode)
        elif isinstance(stmt, Comment):
            self._emit_comment(stmt, indent_level)
        else:
            raise TypeError(f"Unknown statement: {type(stmt)}")

    def _emit_mem_write(self, stmt: MemWrite, indent_level: int, mode: str) -> None:
        prefix = self.indent * indent_level
        op = "<=" if mode == "seq" else "="
        addr = self._emit_expr(stmt.addr)
        value = self._emit_expr(stmt.value)
        memory = self._memory_decl_map.get(stmt.mem_name)
        byte_enable = getattr(stmt, "byte_enable", None)
        if byte_enable is None:
            self.lines.append(f"{prefix}{stmt.mem_name}[{addr}] {op} {value};")
            return
        if memory is None or getattr(memory, "byte_enable_granularity", None) is None:
            raise NotImplementedError(
                f"memory '{stmt.mem_name}' uses byte-enable writes but does not expose "
                "byte_enable_granularity metadata to the emitter"
            )
        granularity = int(memory.byte_enable_granularity)
        lane_count = int(memory.width) // granularity
        be_expr = self._emit_expr(byte_enable)
        for lane_idx in range(lane_count):
            lo = lane_idx * granularity
            hi = lo + granularity - 1
            self.lines.append(
                f"{prefix}if ({be_expr}[{lane_idx}]) {stmt.mem_name}[{addr}][{hi}:{lo}] {op} {value}[{hi}:{lo}];"
            )

    def _collect_assigned_targets(self, body: List[Any]) -> set:
        targets = set()
        for stmt in body:
            if isinstance(stmt, Assign):
                if isinstance(stmt.target, Signal):
                    targets.add(stmt.target)
            elif isinstance(stmt, IfNode):
                targets.update(self._collect_assigned_targets(stmt.then_body))
                for _, body in stmt.elif_bodies:
                    targets.update(self._collect_assigned_targets(body))
                targets.update(self._collect_assigned_targets(stmt.else_body))
            elif isinstance(stmt, WhenNode):
                for _, body in stmt.branches:
                    targets.update(self._collect_assigned_targets(body))
            elif isinstance(stmt, SwitchNode):
                for _, case_body in stmt.cases:
                    targets.update(self._collect_assigned_targets(case_body))
                targets.update(self._collect_assigned_targets(stmt.default_body))
            elif isinstance(stmt, (ForGenNode, GenIfNode)):
                targets.update(self._collect_assigned_targets(stmt.body))
                if hasattr(stmt, 'else_body'):
                    targets.update(self._collect_assigned_targets(stmt.else_body))
        return targets

    def _is_simple_comb_block(self, body: List[Any]) -> bool:
        """判断 comb block 是否仅由 assign / indexed assign / array write / comment 组成。"""
        for stmt in body:
            if not isinstance(stmt, (Assign, IndexedAssign, ArrayWrite, Comment)):
                return False
        # If the same signal is assigned more than once, we must use always @(*)
        # so that later assignments override earlier ones (procedural semantics).
        seen = set()
        for stmt in body:
            if isinstance(stmt, Assign):
                target = stmt.target
                if isinstance(target, Signal):
                    if id(target) in seen:
                        return False
                    seen.add(id(target))
            elif isinstance(stmt, IndexedAssign):
                target = stmt.target_signal
                if id(target) in seen:
                    return False
                seen.add(id(target))
        return True

    def _emit_cse_decls(self, cse_wires: List[Signal]):
        for w in cse_wires:
            if w.width == 1:
                self.lines.append(f"    logic {w.name};")
            else:
                self.lines.append(f"    logic [{w.width - 1}:0] {w.name};")
        if cse_wires:
            self._append_blank_line()

    def _emit_simple_comb(self, body: List[Any], doc_comment: str = ""):
        """Emit simple comb block as assign statements.

        If doc_comment is provided, emit a key comment before the block.
        """
        if doc_comment and self._emit_block_comments:
            self.lines.append(f"    // Comb: {doc_comment}")
        has_mux_chain = any(
            isinstance(stmt, Assign) and isinstance(stmt.target, Signal) and self._is_mux_chain(stmt.value) for stmt in body
        )
        if has_mux_chain:
            if not self.disable_cse:
                body = self._cse_pass(body)
                extra_wires = []
            elif self._enable_complexity_extraction and self._needs_complexity_extraction(body):
                body, extra_wires = self._complexity_pass(body)
            else:
                extra_wires = []
            cse_wires = []
            cse_assigns = []
            rest = []
            for stmt in body:
                if isinstance(stmt, Assign) and isinstance(stmt.target, Wire) and stmt.target.name.startswith("_cse_"):
                    cse_wires.append(stmt.target)
                    cse_assigns.append(stmt)
                else:
                    rest.append(stmt)
            self._emit_cse_decls(cse_wires)
            if extra_wires:
                self._emit_cse_decls(extra_wires)
            keyword = "always_comb" if self.use_sv_always else "always @(*)"
            self.lines.append(f"    {keyword} begin")
            for stmt in cse_assigns:
                lhs = self._emit_lhs(stmt.target)
                self.lines.append(f"        {lhs} = {self._emit_expr(stmt.value)};")
            for stmt in rest:
                if isinstance(stmt, Assign):
                    if isinstance(stmt.target, Signal) and self._is_mux_chain(stmt.value):
                        self._emit_mux_chain_as_case(stmt.target.name, stmt.value, 2, "comb")
                    else:
                        lhs = self._emit_lhs(stmt.target)
                        self.lines.append(f"        {lhs} = {self._emit_assign_rhs(stmt.value, stmt.target)};")
                elif isinstance(stmt, IndexedAssign):
                    tname = self._prefixed_name(stmt.target_signal)
                    if stmt.target_signal.width == 1:
                        self.lines.append(f"        {tname} = {self._emit_expr(stmt.value)};")
                    else:
                        self.lines.append(
                            f"        {tname}[{self._emit_expr(stmt.index)}] = {self._emit_expr(stmt.value)};"
                        )
                elif isinstance(stmt, ArrayWrite):
                    self.lines.append(
                        f"        {stmt.array_name}[{self._emit_expr(stmt.index)}] = {self._emit_expr(stmt.value)};"
                    )
                elif isinstance(stmt, Comment):
                    self._emit_comment(stmt, indent_level=2)
            self.lines.append("    end")
            self._append_blank_line()
            return

        if not self.disable_cse:
            body = self._cse_pass(body)
            extra_wires: List[Signal] = []
        elif self._enable_complexity_extraction and self._needs_complexity_extraction(body):
            body, extra_wires = self._complexity_pass(body)
        else:
            extra_wires = []
        cse_wires = []
        cse_assigns = []
        rest = []
        for stmt in body:
            if isinstance(stmt, Assign) and isinstance(stmt.target, Wire) and stmt.target.name.startswith("_cse_"):
                cse_wires.append(stmt.target)
                cse_assigns.append(stmt)
            else:
                rest.append(stmt)
        self._emit_cse_decls(cse_wires)
        # Emit complexity-extracted wire declarations
        if extra_wires:
            self._emit_cse_decls(extra_wires)
        for stmt in cse_assigns:
            lhs = self._emit_lhs(stmt.target)
            rhs = self._emit_expr(stmt.value)
            self.lines.append(f"    assign {lhs} = {rhs};")
        for stmt in rest:
            if isinstance(stmt, Assign):
                rhs = self._emit_assign_rhs(stmt.value, stmt.target)
                lhs = self._emit_lhs(stmt.target)
                self.lines.append(f"    assign {lhs} = {rhs};")
            elif isinstance(stmt, IndexedAssign):
                rhs = self._emit_expr(stmt.value)
                tname = self._prefixed_name(stmt.target_signal)
                if stmt.target_signal.width == 1:
                    self.lines.append(f"    assign {tname} = {rhs};")
                else:
                    self.lines.append(
                        f"    assign {tname}[{self._emit_expr(stmt.index)}] = {rhs};"
                    )
            elif isinstance(stmt, ArrayWrite):
                rhs = self._emit_expr(stmt.value)
                self.lines.append(
                    f"    assign {stmt.array_name}[{self._emit_expr(stmt.index)}] = {rhs};"
                )
            elif isinstance(stmt, Comment):
                self._emit_comment(stmt, indent_level=1)
        if body:
            self._append_blank_line()

    def _expr_signature(self, expr: Any) -> tuple:
        if isinstance(expr, Const):
            return ("const", int(expr.value), expr.width)
        if isinstance(expr, Ref):
            return ("ref", expr.signal.name)
        if isinstance(expr, BinOp):
            return ("binop", expr.op, self._expr_signature(expr.lhs), self._expr_signature(expr.rhs), expr.width)
        if isinstance(expr, UnaryOp):
            return ("unary", expr.op, self._expr_signature(expr.operand), expr.width)
        if isinstance(expr, Mux):
            return ("mux", self._expr_signature(expr.cond), self._expr_signature(expr.true_expr), self._expr_signature(expr.false_expr), expr.width)
        if isinstance(expr, Concat):
            return ("concat", tuple(self._expr_signature(op) for op in expr.operands), expr.width)
        if isinstance(expr, Slice):
            return ("slice", self._expr_signature(expr.operand), expr.hi, expr.lo, expr.width)
        if isinstance(expr, PartSelect):
            return ("partsel", self._expr_signature(expr.operand), self._expr_signature(expr.offset), expr.width)
        if isinstance(expr, BitSelect):
            return ("bitsel", self._expr_signature(expr.operand), self._expr_signature(expr.index), expr.width)
        return ("unknown", type(expr).__name__, id(expr))

    def _cse_pass(self, body: List[Any]) -> List[Any]:
        subexprs = {}

        def collect_expr(expr):
            if expr is None or isinstance(expr, (int, GenVar)):
                return
            sig = self._expr_signature(expr)
            if sig in subexprs:
                subexprs[sig][1] += 1
            else:
                subexprs[sig] = [expr, 1]
            if isinstance(expr, BinOp):
                collect_expr(expr.lhs)
                collect_expr(expr.rhs)
            elif isinstance(expr, Mux):
                collect_expr(expr.cond)
                collect_expr(expr.true_expr)
                collect_expr(expr.false_expr)
            elif isinstance(expr, UnaryOp):
                collect_expr(expr.operand)
            elif isinstance(expr, (Slice, PartSelect, BitSelect)):
                collect_expr(expr.operand)
                if hasattr(expr, 'index'):
                    collect_expr(expr.index)
                if hasattr(expr, 'offset'):
                    collect_expr(expr.offset)
            elif isinstance(expr, Concat):
                for op in expr.operands:
                    collect_expr(op)

        def collect_stmt(stmt):
            if isinstance(stmt, Assign):
                collect_expr(stmt.value)
            elif isinstance(stmt, IndexedAssign):
                collect_expr(stmt.index)
                collect_expr(stmt.value)
            elif isinstance(stmt, IfNode):
                collect_expr(stmt.cond)
                for s in stmt.then_body:
                    collect_stmt(s)
                for cond, body in stmt.elif_bodies:
                    collect_expr(cond)
                    for s in body:
                        collect_stmt(s)
                for s in stmt.else_body:
                    collect_stmt(s)
            elif isinstance(stmt, WhenNode):
                for cond, body in stmt.branches:
                    if cond is not None:
                        collect_expr(cond)
                    for s in body:
                        collect_stmt(s)
            elif isinstance(stmt, SwitchNode):
                collect_expr(stmt.expr)
                for _, case_body in stmt.cases:
                    for s in case_body:
                        collect_stmt(s)
                for s in stmt.default_body:
                    collect_stmt(s)
            elif isinstance(stmt, (ArrayWrite, MemWrite)):
                collect_expr(stmt.index if hasattr(stmt, 'index') else stmt.addr)
                collect_expr(stmt.value)

        for stmt in body:
            collect_stmt(stmt)

        # 找出重复的非平凡子表达式
        duplicates = {}
        for sig, (expr, count) in subexprs.items():
            if count > 1 and isinstance(expr, (BinOp, UnaryOp, Mux, Concat)):
                duplicates[sig] = expr

        if not duplicates:
            return body

        replacements = {}
        new_stmts = []
        for sig, expr in duplicates.items():
            wire_name = f"_cse_{self._cse_counter}"
            self._cse_counter += 1
            wire = Wire(expr.width, wire_name)
            new_stmts.append(Assign(wire, expr, blocking=True))
            replacements[sig] = wire

        def replace_expr(expr):
            sig = self._expr_signature(expr)
            if sig in replacements:
                return Ref(replacements[sig])
            if isinstance(expr, BinOp):
                return BinOp(expr.op, replace_expr(expr.lhs), replace_expr(expr.rhs), expr.width)
            if isinstance(expr, UnaryOp):
                return UnaryOp(expr.op, replace_expr(expr.operand), expr.width)
            if isinstance(expr, Mux):
                return Mux(replace_expr(expr.cond), replace_expr(expr.true_expr), replace_expr(expr.false_expr), expr.width)
            if isinstance(expr, Concat):
                return Concat([replace_expr(op) for op in expr.operands], expr.width)
            if isinstance(expr, Slice):
                return Slice(replace_expr(expr.operand), expr.hi, expr.lo)
            if isinstance(expr, PartSelect):
                return PartSelect(replace_expr(expr.operand), replace_expr(expr.offset), expr.width)
            if isinstance(expr, BitSelect):
                return BitSelect(replace_expr(expr.operand), replace_expr(expr.index))
            return expr

        def replace_stmt(stmt):
            if isinstance(stmt, Assign):
                return Assign(stmt.target, replace_expr(stmt.value), stmt.blocking)
            if isinstance(stmt, IndexedAssign):
                return IndexedAssign(stmt.target_signal, replace_expr(stmt.index), replace_expr(stmt.value), stmt.blocking)
            if isinstance(stmt, IfNode):
                new_if = IfNode(replace_expr(stmt.cond))
                new_if.then_body = [replace_stmt(s) for s in stmt.then_body]
                new_if.elif_bodies = [(replace_expr(c), [replace_stmt(s) for s in b]) for c, b in stmt.elif_bodies]
                new_if.else_body = [replace_stmt(s) for s in stmt.else_body]
                return new_if
            if isinstance(stmt, SwitchNode):
                new_sw = SwitchNode(replace_expr(stmt.expr))
                new_sw.cases = [(replace_expr(val), [replace_stmt(s) for s in case_body]) for val, case_body in stmt.cases]
                new_sw.default_body = [replace_stmt(s) for s in stmt.default_body]
                return new_sw
            if isinstance(stmt, (ArrayWrite, MemWrite)):
                # 简化：不深入处理
                pass
            return stmt

        result = list(new_stmts)
        for stmt in body:
            result.append(replace_stmt(stmt))
        return result

    def _auto_always_comment(self, body: List[Any], block_type: str) -> str:
        """Auto-generate a comment for an always block by analyzing assigned targets."""
        targets: set = set()
        def _gather(stmts):
            for s in stmts:
                if isinstance(s, Assign) and isinstance(s.target, Signal):
                    targets.add(s.target.name)
                elif isinstance(s, IfNode):
                    _gather(s.then_body)
                    for _, b in s.elif_bodies:
                        _gather(b)
                    _gather(s.else_body)
                elif isinstance(s, SwitchNode):
                    for _, b in s.cases:
                        _gather(b)
                    _gather(s.default_body)
        _gather(body)
        if not targets:
            return ""
        sorted_targets = sorted(targets)
        if len(sorted_targets) <= 3:
            target_str = ", ".join(sorted_targets)
        else:
            target_str = ", ".join(sorted_targets[:3]) + f" (+{len(sorted_targets) - 3})"
        return target_str

    def _emit_always_comb(self, body: List[Any], doc_comment: str = ""):
        """Emit a combinational logic block.

        If doc_comment is provided, emit a key comment before the block
        explaining what it does.
        """
        keyword = "always_comb" if self.use_sv_always else "always @(*)"
        if not self.disable_cse:
            body = self._cse_pass(body)

        cse_wires = []
        cse_assigns = []
        rest = []
        for stmt in body:
            if isinstance(stmt, Assign) and isinstance(stmt.target, Wire) and stmt.target.name.startswith("_cse_"):
                cse_wires.append(stmt.target)
                cse_assigns.append(stmt)
            else:
                rest.append(stmt)

        for w in cse_wires:
            if w.width == 1:
                self.lines.append(f"    logic {w.name};")
            else:
                self.lines.append(f"    logic [{w.width - 1}:0] {w.name};")
        if cse_wires:
            self._append_blank_line()

        if doc_comment and self._emit_block_comments:
            self.lines.append(f"    // Comb: {doc_comment}")
        self.lines.append(f"    {keyword} begin")
        for stmt in cse_assigns:
            self._emit_stmt(stmt, 2, "comb")
        for stmt in rest:
            self._emit_stmt(stmt, 2, "comb")
        self.lines.append("    end")
        self._append_blank_line()

    def _emit_else_chain(self, stmt: IfNode, indent_level: int, mode: str):
        prefix = self.indent * indent_level
        for cond, body in stmt.elif_bodies:
            self.lines.append(f"{prefix}end else if ({self._emit_expr(cond)}) begin")
            for s in body:
                self._emit_stmt(s, indent_level + 1, mode)
        if stmt.else_body:
            # Flatten else { if (...) } → else if (...)
            if len(stmt.else_body) == 1 and isinstance(stmt.else_body[0], IfNode):
                inner = stmt.else_body[0]
                self.lines.append(f"{prefix}end else if ({self._emit_expr(inner.cond)}) begin")
                for s in inner.then_body:
                    self._emit_stmt(s, indent_level + 1, mode)
                self._emit_else_chain(inner, indent_level, mode)
            else:
                self.lines.append(f"{prefix}end else begin")
                for s in stmt.else_body:
                    self._emit_stmt(s, indent_level + 1, mode)
                self.lines.append(f"{prefix}end")
        else:
            self.lines.append(f"{prefix}end")

    def _emit_when(self, stmt: Any, indent_level: int, mode: str):
        """Emit WhenNode as a series of if/else if/else blocks."""
        prefix = self.indent * indent_level
        first = True
        for cond, body in stmt.branches:
            if cond is None:
                # otherwise branch
                self.lines.append(f"{prefix}end else begin")
            elif first:
                self.lines.append(f"{prefix}if ({self._emit_expr(cond)}) begin")
                first = False
            else:
                self.lines.append(f"{prefix}end else if ({self._emit_expr(cond)}) begin")
            for s in body:
                self._emit_stmt(s, indent_level + 1, mode)
        self.lines.append(f"{prefix}end")

    def _emit_always_latch(self, body: List[Any]):
        """Emit always_latch block."""
        keyword = "always_latch" if self.use_sv_always else "always @(*)"  # lint: always_latch
        self.lines.append(f"    {keyword} begin")
        for stmt in body:
            self._emit_stmt(stmt, indent_level=2, mode="comb")
        self.lines.append("    end")
        self._append_blank_line()

    def _emit_initial(self, body: List[Any]):
        """Emit initial block."""
        self.lines.append("    initial begin")
        for stmt in body:
            self._emit_stmt(stmt, indent_level=2, mode="seq")
        self.lines.append("    end")
        self._append_blank_line()

    def _emit_always_seq(self, clk: Signal, rst: Optional[Signal], reset_async: bool, reset_active_low: bool, body: List[Any], doc_comment: str = ""):
        """Emit a sequential logic block.

        If doc_comment is provided, emit a key comment before the block
        explaining what it does.
        """
        # Helper: resolve reset signal name and polarity from expressions like ~rst_n
        def _resolve_reset(r):
            if r is None:
                return None, reset_async, reset_active_low
            if isinstance(r, Signal) and r.name:
                return r.name, reset_async, reset_active_low
            if isinstance(r, Signal) and hasattr(r, '_expr'):
                expr = r._expr
                if isinstance(expr, UnaryOp) and expr.op == '~':
                    inner = expr.operand
                    if isinstance(inner, Ref):
                        return inner.signal.name, True, True
                    if isinstance(inner, Signal):
                        return inner.name, True, True
            return None, reset_async, reset_active_low

        rst_name, rst_async, rst_active_low = _resolve_reset(rst)

        # Profile override for reset style
        reset_style = self.profile.reset_style if self.profile else None
        if reset_style == "sync":
            # Synchronous reset: omit reset from sensitivity list
            sens = f"posedge {clk.name}"
        elif reset_style == "async_high":
            sens = f"posedge {clk.name} or posedge {rst_name}" if rst_name is not None else f"posedge {clk.name}"
        elif reset_style == "async_low":
            sens = f"posedge {clk.name} or negedge {rst_name}" if rst_name is not None else f"posedge {clk.name}"
        else:
            # Fallback to decorator-provided settings
            if rst_name is not None and rst_async:
                if rst_active_low:
                    sens = f"posedge {clk.name} or negedge {rst_name}"
                else:
                    sens = f"posedge {clk.name} or posedge {rst_name}"
            else:
                sens = f"posedge {clk.name}"

        # Profile override for always_ff
        use_always_ff = self.use_sv_always or (self.profile is not None and self.profile.always_ff)
        keyword = "always_ff" if use_always_ff else "always"

        if self._emit_block_comments:
            timing_summary = self._format_seq_timing_comment(
                clk=clk,
                rst_name=rst_name,
                rst_async=rst_async,
                rst_active_low=rst_active_low,
            )
            self.lines.append(f"    // Seq timing: {timing_summary}")
            if doc_comment:
                self.lines.append(f"    // Seq: {doc_comment}")
        self.lines.append(f"    {keyword} @({sens}) begin")
        for stmt in body:
            self._emit_stmt(stmt, 2, "seq")
        self.lines.append("    end")
        self._append_blank_line()

    def _format_seq_timing_comment(
        self,
        *,
        clk: Signal,
        rst_name: Optional[str],
        rst_async: bool,
        rst_active_low: bool,
    ) -> str:
        parts = [f"clk={clk.name}"]
        if rst_name is None:
            parts.append("reset=none")
        else:
            reset_mode = "async" if rst_async else "sync"
            reset_polarity = "active-low" if rst_active_low else "active-high"
            parts.append(f"reset={rst_name} ({reset_mode}, {reset_polarity})")
        return ", ".join(parts)

    def _emit_for_gen(self, stmt: Any, indent_level: int, mode: str):
        prefix = self.indent * indent_level
        step = getattr(stmt, 'step', 1)
        if step > 0:
            cond_op = "<"
            step_expr = f"{stmt.var_name} + {step}"
        elif step < 0:
            cond_op = ">"
            step_expr = f"{stmt.var_name} - {-step}"
        else:
            raise ValueError("ForGen step cannot be zero")
        if mode == "assign":
            # 模块顶层：使用 genvar + generate for
            self.lines.append(f"{prefix}genvar {stmt.var_name};")
            self.lines.append(
                f"{prefix}for ({stmt.var_name} = {stmt.start}; "
                f"{stmt.var_name} {cond_op} {stmt.end}; "
                f"{stmt.var_name} = {step_expr}) begin : genblk"
            )
        else:
            # always 块内：使用 integer for
            self.lines.append(
                f"{prefix}for (integer {stmt.var_name} = {stmt.start}; "
                f"{stmt.var_name} {cond_op} {stmt.end}; "
                f"{stmt.var_name} = {step_expr}) begin"
            )
        for s in stmt.body:
            self._emit_stmt(s, indent_level + 1, mode)
        self.lines.append(f"{prefix}end")

    def _emit_gen_if(self, stmt: GenIfNode, indent_level: int):
        prefix = self.indent * indent_level
        self.lines.append(f"{prefix}if ({self._emit_expr(stmt.cond)}) begin : genif")
        for s in stmt.then_body:
            self._emit_stmt(s, indent_level + 1, "assign")
        for cond, body in stmt.elif_bodies:
            self.lines.append(f"{prefix}end else if ({self._emit_expr(cond)}) begin : genelif")
            for s in body:
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
        mod_name = self._emitted_sv_module_name(mod)
        params = stmt.params
        if params:
            plist = ", ".join(f".{k}({self._emit_param_override(v)})" for k, v in params.items())
            self.lines.append(f"{prefix}{mod_name} #({plist}) {stmt.name} (")
        else:
            self.lines.append(f"{prefix}{mod_name} {stmt.name} (")

        port_map = stmt.port_map
        items = [(k, v) for k, v in port_map.items() if v is not None]
        output_ports = set(stmt.module._outputs.keys())
        # Also connect unconnected output ports to their prefix wires
        for port_name in output_ports:
            if port_name not in port_map:
                items.append((port_name, Ref(Wire(stmt.module._outputs[port_name].width, f"{stmt.name}_{port_name}"))))
        for i, (port_name, expr) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            expr_obj = _to_expr(expr) if isinstance(expr, Signal) else expr
            if self._submodule_port_expr_needs_helper(expr_obj):
                wire_name = self._port_expr_map[(stmt.name, port_name)]
                width = expr_obj.width
                expr_obj = Ref(Wire(width, wire_name))
            # For output ports, emit bare name without $signed() wrapper
            # because Verilog does not allow $signed() in output port connections
            if port_name in output_ports:
                expr_str = self._emit_expr(expr_obj, for_lhs=True)
            else:
                expr_str = self._emit_expr(expr_obj)
            self.lines.append(f"{inner}.{port_name}({expr_str}){comma}")
        self.lines.append(f"{prefix});")
        self._append_blank_line()

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

    def _resolve_cross_module_assignments(self, module: Module):
        """Audit Fix 0522 — Section 2.2: Convert cross-module assignments
        (e.g., submod.port <<= self.sig) into proper port_map entries for
        implicit submodules, and remove the original Assign statements
        to avoid redundant "assign x = x;" output.

        This handles two patterns:
        1. self.sub = SubModule()  (registered in _submodules via __setattr__)
        2. sub = SubModule()       (local variable, connected via direct assignment)
        """
        from rtlgen_x.dsl.core import Assign, Input, Output, Signal, SubmoduleInst

        # =====================================================================
        # Phase 1: Detect local-variable submodules from cross-module assignments
        # =====================================================================
        # Scan all Assign statements to find targets that belong to a submodule
        # not yet registered in module._submodules.
        local_submod_ports: Dict[int, Dict[str, Any]] = {}  # id(submod) -> info

        def _collect_local_submods(body: List[Any]) -> List[int]:
            to_remove: List[int] = []
            for i, stmt in enumerate(body):
                if not isinstance(stmt, Assign):
                    continue
                target = stmt.target
                if not isinstance(target, Signal):
                    continue
                if not hasattr(target, '_parent_module') or target._parent_module is None:
                    continue
                submod = target._parent_module
                if submod is module:
                    continue
                if not isinstance(submod, Module):
                    continue
                # Skip if already registered in _submodules
                if any(id(s) == id(submod) for _, s in module._submodules):
                    continue

                # Find port name in the submodule
                port_name = None
                for pname, psig in list(submod._inputs.items()) + list(submod._outputs.items()):
                    if psig is target:
                        port_name = pname
                        break
                if port_name is None:
                    continue

                submod_id = id(submod)
                if submod_id not in local_submod_ports:
                    # Generate a unique instance name
                    base_name = getattr(submod, '_type_name', submod.name)
                    existing_names = {n for n, _ in module._submodules}
                    for info in local_submod_ports.values():
                        existing_names.add(info["inst_name"])
                    inst_name = base_name
                    if inst_name in existing_names:
                        j = 1
                        while f"{inst_name}_{j}" in existing_names:
                            j += 1
                        inst_name = f"{inst_name}_{j}"
                    local_submod_ports[submod_id] = {
                        "submod": submod,
                        "inst_name": inst_name,
                        "ports": {},
                    }

                local_submod_ports[submod_id]["ports"][port_name] = stmt.value
                to_remove.append(i)
            return to_remove

        # Scan _top_level
        top_remove = _collect_local_submods(module._top_level)
        for i in reversed(top_remove):
            module._top_level.pop(i)

        # Scan _comb_blocks
        for body in module._comb_blocks:
            comb_remove = _collect_local_submods(body)
            for i in reversed(comb_remove):
                body.pop(i)

        # Register local submodules and create SubmoduleInst nodes
        for info in local_submod_ports.values():
            submod = info["submod"]
            inst_name = info["inst_name"]
            port_map = info["ports"]

            # Add to _submodules
            module._submodules.append((inst_name, submod))
            # Create SubmoduleInst — values may be Signal or Expr, both are fine
            inst = SubmoduleInst(inst_name, submod, {}, port_map)
            module._top_level.append(inst)

        # =====================================================================
        # Phase 2: Original logic — remove redundant assigns for ALL registered
        # submodules (including those just registered in Phase 1).
        # =====================================================================
        submod_port_map: Dict[int, Tuple[str, Module, str]] = {}
        for inst_name, submod in module._submodules:
            for pname, sig in submod._inputs.items():
                submod_port_map[id(sig)] = (inst_name, submod, pname)
            for pname, sig in submod._outputs.items():
                submod_port_map[id(sig)] = (inst_name, submod, pname)

        if not submod_port_map:
            return

        # Scan top-level assigns for cross-module connections
        to_remove: List[int] = []
        for i, stmt in enumerate(module._top_level):
            if not isinstance(stmt, Assign):
                continue
            target_id = id(stmt.target) if hasattr(stmt.target, '__class__') else None
            if target_id and target_id in submod_port_map:
                to_remove.append(i)

        # Remove cross-module assigns in reverse order to preserve indices
        for i in reversed(to_remove):
            module._top_level.pop(i)

        # Also scan comb blocks for cross-module assigns
        for body in module._comb_blocks:
            to_remove_comb: List[int] = []
            for i, stmt in enumerate(body):
                if not isinstance(stmt, Assign):
                    continue
                target_id = id(stmt.target) if hasattr(stmt.target, '__class__') else None
                if target_id and target_id in submod_port_map:
                    to_remove_comb.append(i)
            for i in reversed(to_remove_comb):
                body.pop(i)

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
                # Even simple comb blocks may be wrapped in always @(*) if they
                # contain mux chains (CSE pass wraps them for readability).
                # If any statement has a mux chain, ALL outputs in the block
                # will be emitted inside that always.
                has_mux_chain = any(
                    isinstance(stmt, Assign) and self._is_mux_chain(stmt.value)
                    for stmt in body
                )
                if has_mux_chain:
                    for stmt in body:
                        if isinstance(stmt, Assign) and isinstance(stmt.target, Output):
                            reg_outputs.add(stmt.target.name)
                continue
            for stmt in body:
                self._scan_stmt_for_reg_outputs(stmt, "comb", reg_outputs)
        for clk, rst, reset_async, reset_active_low, body in module._seq_blocks:
            for stmt in body:
                self._scan_stmt_for_reg_outputs(stmt, "seq", reg_outputs)
        return reg_outputs

    def _extract_output_signal(self, expr):
        if isinstance(expr, Output):
            return expr
        if isinstance(expr, (Slice, PartSelect, BitSelect)):
            return self._extract_output_signal(expr.operand)
        if isinstance(expr, Ref):
            return self._extract_output_signal(expr.signal)
        return None

    def _scan_stmt_for_reg_outputs(self, stmt: Any, mode: str, reg_outputs: set):
        if isinstance(stmt, Assign):
            target = self._extract_output_signal(stmt.target)
            if isinstance(target, Output) and mode in ("comb", "seq"):
                reg_outputs.add(target.name)
        elif isinstance(stmt, IndexedAssign):
            if isinstance(stmt.target_signal, Output) and mode in ("comb", "seq"):
                reg_outputs.add(stmt.target_signal.name)
        elif isinstance(stmt, IfNode):
            for s in stmt.then_body:
                self._scan_stmt_for_reg_outputs(s, mode, reg_outputs)
            for _, body in stmt.elif_bodies:
                for s in body:
                    self._scan_stmt_for_reg_outputs(s, mode, reg_outputs)
            for s in stmt.else_body:
                self._scan_stmt_for_reg_outputs(s, mode, reg_outputs)
        elif isinstance(stmt, WhenNode):
            for _, body in stmt.branches:
                for s in body:
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
    # Complexity-based sub-expression extraction
    # -----------------------------------------------------------------
    # When CSE is disabled (user wants readable RTL), overly complex
    # expressions still get fully inlined into unreadable mega-lines.
    # This pass detects expressions that exceed complexity thresholds
    # and extracts them into named intermediate wires, even if they
    # only appear once.
    # -----------------------------------------------------------------

    _COMPLEXITY_DEPTH_LIMIT = 4      # max tree depth before extraction
    _COMPLEXITY_CHAR_LIMIT = 300     # max emitted chars before extraction
    _COMPLEXITY_NODE_LIMIT = 20      # max AST nodes before extraction
    _READABILITY_CHAIN_TERM_LIMIT = 4

    def _expr_depth(self, expr: Any) -> int:
        """Maximum nesting depth of an expression tree."""
        if expr is None or isinstance(expr, (int, Const, GenVar, Signal)):
            return 0
        if isinstance(expr, Ref):
            return 0
        if isinstance(expr, (UnaryOp, Slice)):
            return 1 + self._expr_depth(getattr(expr, 'operand', None))
        if isinstance(expr, (PartSelect, BitSelect)):
            return 1 + max(
                self._expr_depth(expr.operand),
                self._expr_depth(getattr(expr, 'index', getattr(expr, 'offset', None)))
            )
        if isinstance(expr, BinOp):
            return 1 + max(self._expr_depth(expr.lhs), self._expr_depth(expr.rhs))
        if isinstance(expr, Mux):
            return 1 + max(
                self._expr_depth(expr.cond),
                self._expr_depth(expr.true_expr),
                self._expr_depth(expr.false_expr)
            )
        if isinstance(expr, Concat):
            return 1 + max((self._expr_depth(op) for op in expr.operands), default=0)
        return 0

    def _expr_node_count(self, expr: Any) -> int:
        """Total number of non-trivial AST nodes."""
        if expr is None or isinstance(expr, (int, Const, GenVar, Signal)):
            return 0
        if isinstance(expr, Ref):
            return 0
        if isinstance(expr, UnaryOp):
            return 1 + self._expr_node_count(expr.operand)
        if isinstance(expr, (BinOp, Slice)):
            return 1 + self._expr_node_count(getattr(expr, 'lhs', getattr(expr, 'operand', None))) + self._expr_node_count(getattr(expr, 'rhs', None))
        if isinstance(expr, Mux):
            return 1 + self._expr_node_count(expr.cond) + self._expr_node_count(expr.true_expr) + self._expr_node_count(expr.false_expr)
        if isinstance(expr, Concat):
            return 1 + sum(self._expr_node_count(op) for op in expr.operands)
        if isinstance(expr, (PartSelect, BitSelect)):
            return 1 + self._expr_node_count(expr.operand)
        return 0

    def _is_too_complex(self, expr: Any) -> bool:
        """Check if an expression exceeds complexity thresholds."""
        try:
            emitted = self._emit_expr(expr)
            if len(emitted) > self._COMPLEXITY_CHAR_LIMIT:
                return True
        except Exception:
            pass
        if self._expr_depth(expr) > self._COMPLEXITY_DEPTH_LIMIT:
            return True
        if self._expr_node_count(expr) > self._COMPLEXITY_NODE_LIMIT:
            return True
        return False

    def _extract_sub_exprs(self, target_name: str, expr: Any,
                           body: list, wire_counter: list) -> Any:
        """Recursively extract complex sub-expressions into named wires.

        Returns the simplified expression (with wire refs replacing extracted parts).
        Appends new Assign statements to `body`.
        """
        if expr is None or isinstance(expr, (int, Const, GenVar, Signal, Ref)):
            return expr
        if not self._is_too_complex(expr):
            return expr

        chain_expr = self._extract_readable_associative_chain(target_name, expr, body, wire_counter)
        if chain_expr is not None:
            return chain_expr

        # Recurse first (deepest-first extraction)
        if isinstance(expr, BinOp):
            new_lhs = self._extract_sub_exprs(target_name, expr.lhs, body, wire_counter)
            new_rhs = self._extract_sub_exprs(target_name, expr.rhs, body, wire_counter)
            result = BinOp(expr.op, new_lhs, new_rhs, expr.width)
            if not self._is_too_complex(result):
                return result
            # Still too complex — extract this node itself
            wire_name = f"_{target_name}_ex{wire_counter[0]}"
            wire_counter[0] += 1
            wire = Wire(getattr(expr, 'width', 1), wire_name)
            body.append(Assign(wire, result, blocking=True))
            return wire
        if isinstance(expr, Mux):
            new_cond = self._extract_sub_exprs(target_name, expr.cond, body, wire_counter)
            new_true = self._extract_sub_exprs(target_name, expr.true_expr, body, wire_counter)
            new_false = self._extract_sub_exprs(target_name, expr.false_expr, body, wire_counter)
            result = Mux(new_cond, new_true, new_false, expr.width)
            if not self._is_too_complex(result):
                return result
            # Still too complex — extract this node itself
            wire_name = f"_{target_name}_ex{wire_counter[0]}"
            wire_counter[0] += 1
            wire = Wire(getattr(expr, 'width', 1), wire_name)
            body.append(Assign(wire, result, blocking=True))
            return wire
        if isinstance(expr, UnaryOp):
            new_op = self._extract_sub_exprs(target_name, expr.operand, body, wire_counter)
            if new_op is expr.operand:
                return expr
            return UnaryOp(expr.op, new_op, expr.width)
        if isinstance(expr, (Slice, PartSelect, BitSelect)):
            new_op = self._extract_sub_exprs(target_name, expr.operand, body, wire_counter)
            if new_op is expr.operand:
                return expr
            # Reconstruct with the exact constructor signature of each type.
            # (A prior getattr-based reconstruction passed the inherited `width`
            # attribute to Slice and dropped BitSelect.index, crashing both.)
            if isinstance(expr, Slice):
                return Slice(new_op, expr.hi, expr.lo)
            if isinstance(expr, PartSelect):
                return PartSelect(new_op, expr.offset, expr.width)
            return BitSelect(new_op, expr.index)
        if isinstance(expr, Concat):
            new_ops = [self._extract_sub_exprs(target_name, op, body, wire_counter) for op in expr.operands]
            if all(n is o for n, o in zip(new_ops, expr.operands)):
                return expr
            return Concat(new_ops, expr.width)

        # If still too complex after recursion, extract this node itself
        wire_name = f"_{target_name}_ex{wire_counter[0]}"
        wire_counter[0] += 1
        wire = Wire(getattr(expr, 'width', 1), wire_name)
        body.append(Assign(wire, expr, blocking=True))
        ref = Ref(wire)
        ref.signal = wire  # ensure signal is set
        return ref

    def _make_signal_ref(self, sig: Signal) -> Ref:
        ref = Ref(sig)
        ref.signal = sig
        return ref

    def _flatten_associative_binop(self, expr: Any, op: str) -> List[Any]:
        if isinstance(expr, BinOp) and expr.op == op:
            return self._flatten_associative_binop(expr.lhs, op) + self._flatten_associative_binop(expr.rhs, op)
        return [expr]

    def _build_left_assoc_binop(self, op: str, operands: List[Any], width: int) -> Any:
        if not operands:
            raise ValueError("operands must not be empty")
        result = operands[0]
        for operand in operands[1:]:
            result = BinOp(op, result, operand, width)
        return result

    def _extract_readable_associative_chain(
        self,
        target_name: str,
        expr: Any,
        body: List[Any],
        wire_counter: List[int],
    ) -> Any | None:
        if not isinstance(expr, BinOp) or expr.op not in {"^", "&", "|"}:
            return None
        operands = self._flatten_associative_binop(expr, expr.op)
        if len(operands) <= self._READABILITY_CHAIN_TERM_LIMIT:
            return None

        simplified_operands = [
            self._extract_sub_exprs(target_name, operand, body, wire_counter)
            for operand in operands
        ]
        current_operands = simplified_operands
        while len(current_operands) > self._READABILITY_CHAIN_TERM_LIMIT:
            next_operands: List[Any] = []
            for index in range(0, len(current_operands), self._READABILITY_CHAIN_TERM_LIMIT):
                chunk = current_operands[index : index + self._READABILITY_CHAIN_TERM_LIMIT]
                if len(chunk) == 1:
                    next_operands.append(chunk[0])
                    continue
                wire_name = f"_{target_name}_ex{wire_counter[0]}"
                wire_counter[0] += 1
                wire = Wire(getattr(expr, "width", 1), wire_name)
                chunk_expr = self._build_left_assoc_binop(expr.op, chunk, expr.width)
                body.append(Assign(wire, chunk_expr, blocking=True))
                next_operands.append(self._make_signal_ref(wire))
            current_operands = next_operands
        return self._build_left_assoc_binop(expr.op, current_operands, expr.width)

    def _complexity_target_name(self, target: Any) -> str:
        """Best-effort stable basename for review-profile helper wires."""
        if isinstance(target, Signal):
            return target.name
        if isinstance(target, Ref):
            return self._complexity_target_name(target.signal)
        if isinstance(target, (Slice, PartSelect, BitSelect)):
            return self._complexity_target_name(target.operand)
        direct_name = getattr(target, "name", None)
        if direct_name:
            return str(direct_name)
        return "tmp"

    def _collect_repeated_subexpr_candidates(
        self,
        expr: Any,
        counts: Dict[tuple, List[Any]],
    ) -> None:
        if expr is None or isinstance(expr, (int, Const, GenVar, Signal, Ref)):
            return
        if isinstance(expr, (BinOp, UnaryOp, Mux, Concat)):
            sig = self._expr_signature(expr)
            if sig in counts:
                counts[sig][1] += 1
            else:
                counts[sig] = [expr, 1]
        if isinstance(expr, BinOp):
            self._collect_repeated_subexpr_candidates(expr.lhs, counts)
            self._collect_repeated_subexpr_candidates(expr.rhs, counts)
            return
        if isinstance(expr, UnaryOp):
            self._collect_repeated_subexpr_candidates(expr.operand, counts)
            return
        if isinstance(expr, Mux):
            self._collect_repeated_subexpr_candidates(expr.cond, counts)
            self._collect_repeated_subexpr_candidates(expr.true_expr, counts)
            self._collect_repeated_subexpr_candidates(expr.false_expr, counts)
            return
        if isinstance(expr, Concat):
            for operand in expr.operands:
                self._collect_repeated_subexpr_candidates(operand, counts)
            return
        if isinstance(expr, Slice):
            self._collect_repeated_subexpr_candidates(expr.operand, counts)
            return
        if isinstance(expr, PartSelect):
            self._collect_repeated_subexpr_candidates(expr.operand, counts)
            self._collect_repeated_subexpr_candidates(expr.offset, counts)
            return
        if isinstance(expr, BitSelect):
            self._collect_repeated_subexpr_candidates(expr.operand, counts)
            self._collect_repeated_subexpr_candidates(expr.index, counts)

    def _replace_expr_by_signature(
        self,
        expr: Any,
        replacements: Dict[tuple, Wire],
        *,
        skip_sig: Optional[tuple] = None,
    ) -> Any:
        if expr is None or isinstance(expr, (int, Const, GenVar, Signal, Ref)):
            return expr
        sig = self._expr_signature(expr)
        if sig != skip_sig and sig in replacements:
            return Ref(replacements[sig])
        if isinstance(expr, BinOp):
            return BinOp(
                expr.op,
                self._replace_expr_by_signature(expr.lhs, replacements, skip_sig=skip_sig),
                self._replace_expr_by_signature(expr.rhs, replacements, skip_sig=skip_sig),
                expr.width,
            )
        if isinstance(expr, UnaryOp):
            return UnaryOp(
                expr.op,
                self._replace_expr_by_signature(expr.operand, replacements, skip_sig=skip_sig),
                expr.width,
            )
        if isinstance(expr, Mux):
            return Mux(
                self._replace_expr_by_signature(expr.cond, replacements, skip_sig=skip_sig),
                self._replace_expr_by_signature(expr.true_expr, replacements, skip_sig=skip_sig),
                self._replace_expr_by_signature(expr.false_expr, replacements, skip_sig=skip_sig),
                expr.width,
            )
        if isinstance(expr, Concat):
            return Concat(
                [self._replace_expr_by_signature(op, replacements, skip_sig=skip_sig) for op in expr.operands],
                expr.width,
            )
        if isinstance(expr, Slice):
            return Slice(
                self._replace_expr_by_signature(expr.operand, replacements, skip_sig=skip_sig),
                expr.hi,
                expr.lo,
            )
        if isinstance(expr, PartSelect):
            return PartSelect(
                self._replace_expr_by_signature(expr.operand, replacements, skip_sig=skip_sig),
                self._replace_expr_by_signature(expr.offset, replacements, skip_sig=skip_sig),
                expr.width,
            )
        if isinstance(expr, BitSelect):
            return BitSelect(
                self._replace_expr_by_signature(expr.operand, replacements, skip_sig=skip_sig),
                self._replace_expr_by_signature(expr.index, replacements, skip_sig=skip_sig),
            )
        return expr

    def _extract_repeated_sub_exprs(
        self,
        target_name: str,
        expr: Any,
        body: List[Any],
        wire_counter: List[int],
    ) -> Any:
        """Extract repeated non-trivial sub-expressions with review-friendly names."""
        counts: Dict[tuple, List[Any]] = {}
        self._collect_repeated_subexpr_candidates(expr, counts)
        duplicates = [
            (sig, counted_expr)
            for sig, (counted_expr, count) in counts.items()
            if count > 1
        ]
        if not duplicates:
            return expr
        duplicates.sort(
            key=lambda item: (
                self._expr_depth(item[1]),
                self._expr_node_count(item[1]),
                self._emit_expr(item[1]),
            )
        )
        replacements: Dict[tuple, Wire] = {}
        for sig, repeated_expr in duplicates:
            wire_name = f"_{target_name}_ex{wire_counter[0]}"
            wire_counter[0] += 1
            replacements[sig] = Wire(getattr(repeated_expr, "width", 1), wire_name)
        for sig, repeated_expr in duplicates:
            wire = replacements[sig]
            body.append(
                Assign(
                    wire,
                    self._replace_expr_by_signature(repeated_expr, replacements, skip_sig=sig),
                    blocking=True,
                )
            )
        return self._replace_expr_by_signature(expr, replacements)

    def _needs_complexity_extraction(self, body: List[Any]) -> bool:
        """Quick check: does any assignment in body have a complex RHS?"""
        for stmt in body:
            if isinstance(stmt, Assign):
                target = stmt.target
                if isinstance(target, Wire) and target.name.startswith("_cse_"):
                    continue
                if self._is_mux_chain(stmt.value):
                    continue
                if self._is_too_complex(stmt.value):
                    return True
        return False

    def _complexity_pass(self, body: List[Any]) -> Tuple[List[Any], List[Signal]]:
        """Extract overly complex expressions into named intermediate wires.

        Returns (new_body, extracted_wires). Extracted wires need declarations.
        """
        new_body = []
        wire_counter = [0]
        extracted_wires: List[Signal] = []

        def extract_with_tracking(target_name, expr, body_out, counter):
            result = self._extract_sub_exprs(target_name, expr, body_out, counter)
            # Collect any new wires added to body_out that we haven't seen
            return result

        for stmt in body:
            if not isinstance(stmt, Assign):
                new_body.append(stmt)
                continue

            target = stmt.target
            if isinstance(target, Wire) and target.name.startswith("_cse_"):
                new_body.append(stmt)
                continue

            # Skip if already a mux chain (handled by _emit_mux_chain_as_case)
            if self._is_mux_chain(stmt.value):
                new_body.append(stmt)
                continue

            target_name = self._complexity_target_name(target)

            if self._is_too_complex(stmt.value):
                local_body: List[Any] = []
                deduped = self._extract_repeated_sub_exprs(target_name, stmt.value, local_body, wire_counter)
                simplified = extract_with_tracking(target_name, deduped, local_body, wire_counter)
                # Collect wires added during extraction
                for s in local_body:
                    if isinstance(s, Assign) and isinstance(s.target, Wire):
                        extracted_wires.append(s.target)
                new_body.extend(local_body)
                new_body.append(Assign(target, simplified, blocking=True))
            else:
                new_body.append(stmt)

        return new_body, extracted_wires

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
            inst_name = getattr(self, '_submod_port_inst_map', {}).get(id(target))
            return f"{inst_name}_{target.name}" if inst_name is not None else target.name
        return self._emit_expr(target, for_lhs=True)

    def _prefixed_name(self, sig: Signal) -> str:
        inst_name = getattr(self, '_submod_port_inst_map', {}).get(id(sig))
        return f"{inst_name}_{sig.name}" if inst_name is not None else sig.name

    def _emit_mux_chain_as_case(self, target_name: str, expr: Expr, indent_level: int, mode: str):
        """将级联 Mux 输出为 case 语句（可选 always @(*) 包装）。"""
        prefix = self.indent * indent_level
        inner = self.indent * (indent_level + 1)
        sel_expr, cases, default_expr = self._extract_mux_chain(expr)
        selector_width = sel_expr.width
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
            width = max(const_val.bit_length(), 1, selector_width)
            self.lines.append(f"{item_prefix}{width}'d{const_val}: {target_name} {op} {self._emit_expr(true_expr)};")
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
        if isinstance(v, str):
            return f'"{v}"'
        return self._emit_expr(_to_expr(v))

    def _precedence(self, op: str) -> int:
        precedence_map = {
            '!': 10, '~': 10,
            '*': 9, '/': 9, '%': 9,
            '+': 8, '-': 8,
            '<<': 7, '>>': 7,
            '<': 6, '<=': 6, '>': 6, '>=': 6,
            '==': 5, '!=': 5, '===': 5, '!==': 5,
            '&': 4,
            '^': 3, '~^': 3,
            '|': 2,
            '&&': 3,
            '||': 2,
            '?': 1,
        }
        return precedence_map.get(op, 0)

    def _is_signed(self, expr: Expr) -> bool:
        """判断表达式是否引用了有符号信号。"""
        if isinstance(expr, Ref):
            return getattr(expr.signal, "signed", False)
        if isinstance(expr, Signal):
            return getattr(expr, "signed", False)
        if isinstance(expr, UnaryOp):
            if expr.op == "$signed":
                return True
            if expr.op == "$unsigned":
                return False
            return self._is_signed(expr.operand)
        if isinstance(expr, BinOp):
            return self._is_signed(expr.lhs) or self._is_signed(expr.rhs)
        return False

    def _emit_expr(self, expr: Expr, parent_op: Optional[str] = None, for_lhs: bool = False) -> str:
        if isinstance(expr, int):
            width = max(expr.bit_length(), 1)
            # Omit width prefix for 0/1 — they are commonly used as indices
            # and are context-independent in most Verilog contexts.
            # Const(0, N) still emits N'd0 via _emit_const_literal.
            if expr == 0 or expr == 1:
                return str(expr)
            return f"{width}'d{expr}"
        if isinstance(expr, Const):
            val = int(expr.value)
            return self._emit_const_literal(val, expr.width)
        if isinstance(expr, Signal):
            # Direct signal reference (including Input, Output, Wire, Reg)
            inst_name = getattr(self, '_submod_port_inst_map', {}).get(id(expr))
            name = f"{inst_name}_{expr.name}" if inst_name is not None else expr.name
            return name
        if isinstance(expr, Ref):
            sig = expr.signal
            inst_name = getattr(self, '_submod_port_inst_map', {}).get(id(sig))
            name = f"{inst_name}_{sig.name}" if inst_name is not None else sig.name
            if getattr(sig, "signed", False) and not for_lhs:
                return f"$signed({name})"
            return name
        if isinstance(expr, BinOp):
            op_str = expr.op

            # Peephole: simplify redundant == 1 / & 1 on 1-bit comparison results
            if op_str == '==' and isinstance(expr.rhs, Const) and int(expr.rhs.value) == 1:
                if isinstance(expr.lhs, BinOp) and expr.lhs.width == 1:
                    return self._emit_expr(expr.lhs, parent_op, for_lhs)
            if op_str == '&':
                if isinstance(expr.rhs, Const) and int(expr.rhs.value) == 1:
                    if isinstance(expr.lhs, BinOp) and expr.lhs.width == 1:
                        return self._emit_expr(expr.lhs, parent_op, for_lhs)
                if isinstance(expr.lhs, Const) and int(expr.lhs.value) == 1:
                    if isinstance(expr.rhs, BinOp) and expr.rhs.width == 1:
                        return self._emit_expr(expr.rhs, parent_op, for_lhs)

            # Arithmetic right shift: emit Verilog >>> operator
            if op_str == '>>>':
                lhs_str = self._emit_expr(expr.lhs, expr.op, for_lhs)
                rhs_str = self._emit_expr(expr.rhs, expr.op, for_lhs)
                s = f"{lhs_str} >>> {rhs_str}"
                if parent_op is not None and self._precedence(expr.op) < self._precedence(parent_op):
                    return f"({s})"
                return s
            # Add parens around comparison operands in bitwise ops (&, |, ^)
            # to prevent Verilog precedence bugs: (a == 0) & (b != 0) not a == 0 & b != 0
            lhs_str = self._emit_expr(expr.lhs, expr.op, for_lhs)
            rhs_str = self._emit_expr(expr.rhs, expr.op, for_lhs)
            if expr.op in ('&', '|', '^'):
                _cmp_ops = ('==', '!=', '<', '>', '<=', '>=')
                if isinstance(expr.lhs, BinOp) and expr.lhs.op in _cmp_ops:
                    lhs_str = f"({lhs_str})"
                if isinstance(expr.rhs, BinOp) and expr.rhs.op in _cmp_ops:
                    rhs_str = f"({rhs_str})"
            s = f"{lhs_str} {expr.op} {rhs_str}"
            if parent_op is not None and self._precedence(expr.op) < self._precedence(parent_op):
                return f"({s})"
            return s
        if isinstance(expr, UnaryOp):
            if expr.op in ("$signed", "$unsigned"):
                inner = self._emit_expr(expr.operand, expr.op, for_lhs)
                return f"{expr.op}({inner})"
            s = f"{expr.op}{self._emit_expr(expr.operand, expr.op, for_lhs)}"
            if parent_op is not None and self._precedence(expr.op) < self._precedence(parent_op):
                return f"({s})"
            return s
        if isinstance(expr, Slice):
            op = expr.operand
            # Handle $signed(signal)[hi:lo] — Verilog does not allow slicing $signed()
            if isinstance(op, Ref) and getattr(op.signal, "signed", False):
                operand_str = self._emit_expr(op, None, for_lhs=True)
            elif isinstance(op, UnaryOp) and op.op == "$signed":
                op = op.operand
                operand_str = self._emit_expr(op, None, for_lhs)
            else:
                operand_str = self._emit_expr(expr.operand, None, for_lhs)
            op_sig = getattr(op, 'signal', op) if isinstance(op, Ref) else op
            if isinstance(op_sig, Signal) and op_sig.width == 1 and expr.hi == 0 and expr.lo == 0:
                return operand_str
            hi, lo = expr.hi, expr.lo
            if hi < lo:
                hi, lo = lo, hi
            if isinstance(expr.operand, (BinOp, UnaryOp, Mux, Concat)):
                # iverilog does not support (expr)[hi:lo]; emulate with shift+mask
                width = hi - lo + 1
                mask = (1 << width) - 1
                if lo == 0:
                    return f"(({operand_str}) & {width}'d{mask})"
                return f"((({operand_str}) >> {lo}) & {width}'d{mask})"
            if isinstance(expr.operand, Slice):
                # Flatten nested slices (e.g. vsrc1[255:240][3:0]) into a single
                # slice on the underlying signal so iverilog can parse it. Walk
                # the chain of nested Slice operands so multi-level nests
                # (3+ deep) collapse to a single index range.
                cur_hi = hi
                cur_lo = lo
                base = expr.operand
                while isinstance(base, Slice):
                    inner_lo = min(base.hi, base.lo)
                    cur_hi = inner_lo + cur_hi
                    cur_lo = inner_lo + cur_lo
                    base = base.operand
                # If the deepest base is an expression iverilog cannot directly
                # part-select (BinOp / UnaryOp / Mux / Concat), the flattened
                # slice cannot be written as ``base[hi:lo]`` — fall back to
                # shift+mask emulation as in the non-flattened branch above.
                if isinstance(base, (BinOp, UnaryOp, Mux, Concat)):
                    base_str = self._emit_expr(base, None, for_lhs)
                    width = cur_hi - cur_lo + 1
                    mask = (1 << width) - 1
                    if cur_lo == 0:
                        return f"(({base_str}) & {width}'d{mask})"
                    return f"((({base_str}) >> {cur_lo}) & {width}'d{mask})"
                base_str = self._emit_expr(base, None, for_lhs)
                if cur_hi == cur_lo:
                    return f"{base_str}[{cur_hi}]"
                return f"{base_str}[{cur_hi}:{cur_lo}]"
            if hi == lo:
                return f"{operand_str}[{hi}]"
            return f"{operand_str}[{hi}:{lo}]"
        if isinstance(expr, PartSelect):
            return f"{self._emit_expr(expr.operand, parent_op, for_lhs)}[{self._emit_expr(expr.offset, parent_op, for_lhs)} +: {expr.width}]"
        if isinstance(expr, Concat):
            ops = expr.operands
            # Detect repetition: {x, x, x, ...} -> {{N{x}}
            if len(ops) > 1:
                first_str = self._emit_expr(ops[0], parent_op, for_lhs)
                all_same = all(self._emit_expr(op, parent_op, for_lhs) == first_str for op in ops)
                if all_same:
                    return f"{{{len(ops)}{{{first_str}}}}}"
            parts = ", ".join(self._emit_expr(op, parent_op, for_lhs) for op in ops)
            return f"{{{parts}}}"
        if isinstance(expr, Mux):
            s = f"{self._emit_expr(expr.cond, '?')} ? {self._emit_expr(expr.true_expr, '?')} : {self._emit_expr(expr.false_expr, '?')}"
            if parent_op is not None and self._precedence('?') < self._precedence(parent_op):
                return f"({s})"
            return s
        if isinstance(expr, MemRead):
            return f"{expr.mem_name}[{self._emit_expr(expr.addr, parent_op)}]"
        if isinstance(expr, ArrayRead):
            return f"{expr.array_name}[{self._emit_expr(expr.index, parent_op)}]"
        if isinstance(expr, BitSelect):
            op = expr.operand
            op_sig = getattr(op, 'signal', op) if isinstance(op, Ref) else op
            if isinstance(op_sig, Signal) and op_sig.width == 1:
                return self._emit_expr(op, parent_op)
            return f"{self._emit_expr(expr.operand, parent_op)}[{self._emit_expr(expr.index, parent_op)}]"
        if isinstance(expr, GenVar):
            return expr.name
        if isinstance(expr, FunctionCall):
            prefix = "$" if expr.is_system else ""
            args = ", ".join(self._emit_expr(a, parent_op) for a in expr.args)
            return f"{prefix}{expr.name}({args})"
        raise TypeError(f"Unknown expression: {type(expr)}")

    def _emit_case_label(self, expr: Expr, selector_width: int) -> str:
        if isinstance(expr, Const):
            width = max(expr.width, selector_width)
            return self._emit_const_literal(int(expr.value), width)
        if isinstance(expr, int):
            width = max(expr.bit_length(), 1, selector_width)
            return self._emit_const_literal(expr, width)
        return self._emit_expr(expr)


def _to_expr(val: Any) -> Expr:
    from rtlgen_x.dsl.core import Parameter
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


# =====================================================================
# Documentation Injection — Mandatory Verilog Comment Injection
# =====================================================================

@dataclass
class ModuleDocTemplate:
    """Structured template for agent-driven Verilog documentation injection.

    Each field has a **prompt** that guides the agent on what to fill in.
    The agent should call ``fill_doc_template(template, module)`` to
    convert the filled template into a ``ModuleDoc`` attached to the module.

    **File-level template fields:**
    - ``source``: Where the DSL came from (e.g., "C910IFU — Phase 3, Step 1")
    - ``description``: What the module does in 1-2 sentences
    - ``author``: Who/agent created it
    - ``version``: Version string (e.g., "1.0", "0.3-beta")
    - ``timing``: Key timing or protocol description (clocks, latencies, handshakes)
    - ``port_description``: Additional notes about ports or interface behavior

    **Per-always-block template entries:**
    Each entry is a dict with:
    - ``block_type``: "Comb" (combinational), "Seq" (sequential), "Reset" (reset handling), "Generate" (generate block)
    - ``targets``: List of signals this block drives
    - ``description``: What this block does in plain language
    - ``timing_notes``: Optional timing notes (e.g., "2-cycle latency", "registered output")
    """
    source: str = ""
    description: str = ""
    author: str = "rtlgen agent"
    version: str = "1.0"
    timing: str = ""
    port_description: str = ""
    always_descriptions: List[Dict[str, str]] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Return a list of validation warnings (empty if all fields are filled)."""
        warnings = []
        if not self.source:
            warnings.append("source: specify where this DSL was generated from")
        if not self.description:
            warnings.append("description: describe what this module does")
        if not self.timing:
            warnings.append("timing: describe key timing or protocol behavior")
        for i, entry in enumerate(self.always_descriptions):
            if "description" not in entry or not entry["description"]:
                warnings.append(f"always_descriptions[{i}]: each block needs a description")
            if "block_type" not in entry or entry["block_type"] not in ("Comb", "Seq", "Reset", "Generate"):
                warnings.append(f"always_descriptions[{i}]: block_type must be Comb/Seq/Reset/Generate")
        return warnings

    def fill_always(self, block_type: str, description: str, timing_notes: str = "",
                    targets: List[str] = None) -> None:
        """Add an always block entry.

        Args:
            block_type: "Comb" | "Seq" | "Reset" | "Generate"
            description: What this block does in plain language
            timing_notes: Optional timing notes
            targets: List of signals this block drives
        """
        entry: Dict[str, Any] = {"block_type": block_type, "description": description}
        if timing_notes:
            entry["timing_notes"] = timing_notes
        if targets:
            entry["targets"] = targets
        self.always_descriptions.append(entry)


def fill_doc_template(template: ModuleDocTemplate, module: Module) -> Module:
    """Convert a filled ModuleDocTemplate into a ModuleDoc attached to the module.

    This is the recommended way for agents to inject documentation.

    Example:
        tpl = ModuleDocTemplate(
            source="C910IFU — Phase 3, Step 1",
            description="Superscalar instruction fetch unit with BTB/BHT/RAS "
                        "branch prediction and 8-wide fetch bandwidth.",
            timing="Multi-cycle pipeline: PCGEN -> BPU lookup -> ICache fetch -> "
                   "output bundle. Flush propagates in 1 cycle.",
        )
        tpl.fill_always("Comb", "PC next selection: redirect target vs PC+increment")
        tpl.fill_always("Comb", "BTB tag match and target lookup")
        tpl.fill_always("Seq", "PC register update with async reset to boot vector")
        fill_doc_template(tpl, ifu_module)
    """
    warnings = template.validate()
    if warnings:
        # Warn but still inject — the agent should fix warnings in development
        import warnings as _warnings
        for w in warnings:
            _warnings.warn(f"ModuleDocTemplate validation: {w}", stacklevel=2)

    always_tuples: List[Tuple[str, str]] = []
    for entry in template.always_descriptions:
        desc = entry.get("description", "")
        timing = entry.get("timing_notes", "")
        if timing:
            desc = f"{desc} ({timing})"
        always_tuples.append((entry["block_type"], desc))

    return inject_doc_comments(
        module,
        source=template.source,
        description=template.description,
        author=template.author,
        version=template.version,
        timing=template.timing,
        port_description=template.port_description,
        always_descriptions=always_tuples,
    )


def inject_doc_comments(
    module: Module,
    *,
    source: str = "",
    description: str = "",
    author: str = "rtlgen agent",
    version: str = "1.0",
    timing: str = "",
    port_description: str = "",
    always_descriptions: Optional[List[Tuple[str, str]]] = None,
    force: bool = True,
) -> Module:
    """Inject structured documentation into a Module for Verilog comment generation.

    This function **must** be called by the agent before emitting any module to
    Verilog. It attaches a ``ModuleDoc`` to the module, which the ``VerilogEmitter``
    uses to generate:

    - File header (module name, source, author, version, description)
    - Port information table
    - Timing / protocol notes
    - Per-always-block key comments (// Comb: ... / // Seq: ...)

    Args:
        module: The DSL Module to annotate.
        source: Where this DSL was generated from (e.g., "C910IFU Phase 3, Step 1").
        description: What this module does in plain language.
        author: Who/agent created it.
        version: Version string.
        timing: Key timing or protocol description.
        port_description: Additional port notes.
        always_descriptions: List of (block_type, description) tuples.
            block_type is one of: "Comb", "Seq", "Reset", "Generate".
        force: If True, overwrite existing _module_doc. If False, only set if missing.

    Returns:
        The same module (for chaining).

    Example:
        inject_doc_comments(
            ifu_module,
            source="C910IFU — Phase 3, Step 1 (Agent implementation)",
            description="Superscalar instruction fetch unit with BTB/BHT/RAS "
                        "branch prediction and 8-wide fetch bandwidth.",
            timing="Multi-cycle pipeline: PCGEN -> BPU lookup -> ICache fetch -> "
                   "output bundle. Flush propagates in 1 cycle.",
            always_descriptions=[
                ("Comb", "PC next selection: redirect target vs PC+increment"),
                ("Comb", "BTB tag match and target lookup"),
                ("Seq", "PC register update with async reset to boot vector"),
                ("Seq", "BHT counter update on branch feedback"),
            ],
        )
    """
    if not force and module._module_doc is not None:
        return module

    if always_descriptions is None:
        always_descriptions = _auto_detect_always_descriptions(module)

    module._module_doc = ModuleDoc(
        source=source,
        description=description,
        author=author,
        version=version,
        timing=timing,
        port_description=port_description,
        always_descriptions=always_descriptions,
    )
    return module


def inject_doc_all_modules(top_module: Module, *, source: str = "",
                           description: str = "", **kwargs) -> Module:
    """Inject documentation into top_module and all its submodules.

    Traverses the module hierarchy and calls inject_doc_comments on each module.
    For submodules, auto-generates source/description from module name and type.

    Returns the top_module (for chaining).
    """
    visited = set()

    def _dfs(mod: Module, parent_path: str):
        if id(mod) in visited:
            return
        visited.add(id(mod))
        path = f"{parent_path}.{mod.name}" if parent_path else mod.name
        mod_source = f"{source} ({path})" if source else f"{path} DSL"
        mod_desc = description or f"{getattr(mod, '_type_name', mod.name)} module"

        # Only inject if module has no doc yet
        if mod._module_doc is None:
            inject_doc_comments(
                mod,
                source=mod_source,
                description=mod_desc,
                **kwargs,
            )

        # Recurse into submodules
        for inst_name, submod in mod._submodules:
            _dfs(submod, path)

        # Recurse into comb/seq block submodules
        def _scan_stmts(stmts):
            for stmt in stmts:
                if isinstance(stmt, SubmoduleInst):
                    _dfs(stmt.module, path)

        for body in mod._comb_blocks:
            _scan_stmts(body)
        for _, _, _, _, body in mod._seq_blocks:
            _scan_stmts(body)
        _scan_stmts(mod._top_level)

    _dfs(top_module, "")
    return top_module


def _auto_detect_always_descriptions(module: Module) -> List[Tuple[str, str]]:
    """Auto-detect always block descriptions by analyzing module structure.

    This is a fallback when the agent does not provide explicit always_descriptions.
    It examines assigned targets and generates descriptive comments.
    """
    docs: List[Tuple[str, str]] = []

    for body in module._comb_blocks:
        targets: set = set()
        for stmt in body:
            if isinstance(stmt, Assign) and isinstance(stmt.target, Signal):
                targets.add(stmt.target.name)
            elif isinstance(stmt, IfNode):
                _collect_target_names(stmt.then_body, targets)
                _collect_target_names(stmt.else_body, targets)
                for _, b in stmt.elif_bodies:
                    _collect_target_names(b, targets)
            elif isinstance(stmt, SwitchNode):
                for _, b in stmt.cases:
                    _collect_target_names(b, targets)
                _collect_target_names(stmt.default_body, targets)
        desc = ", ".join(sorted(targets)[:5])
        if len(targets) > 5:
            desc += f" (+{len(targets) - 5})"
        docs.append(("Comb", desc))

    for _, rst, reset_async, reset_active_low, body in module._seq_blocks:
        targets: set = set()
        _collect_target_names(body, targets)
        if rst is not None:
            rst_type = "async low" if reset_active_low else "async high"
            desc = f"{', '.join(sorted(targets)[:4])} (reset: {rst_type})"
        else:
            desc = ", ".join(sorted(targets)[:5])
        if len(targets) > 5:
            desc += f" (+{len(targets) - 5})"
        docs.append(("Seq", desc))

    return docs


def _collect_target_names(stmts: list, targets: set):
    """Helper: collect signal names from assignment targets in a statement list."""
    for s in stmts:
        if isinstance(s, Assign) and isinstance(s.target, Signal):
            targets.add(s.target.name)
        elif isinstance(s, IfNode):
            _collect_target_names(s.then_body, targets)
            _collect_target_names(s.else_body, targets)
            for _, b in s.elif_bodies:
                _collect_target_names(b, targets)
        elif isinstance(s, SwitchNode):
            for _, b in s.cases:
                _collect_target_names(b, targets)
            _collect_target_names(s.default_body, targets)
