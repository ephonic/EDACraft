"""
rtlgen.sim_jit — JIT-compiled simulation backend

Compiles rtlgen AST into flat Python closures for ~50-500x speedup over
AST interpretation.  Signals are stored in a flat list[int]; expressions
become direct arithmetic on list indices.

Fallback: if compilation fails (e.g. unsupported node), the caller should
use the standard Simulator AST interpreter.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from rtlgen.core import (
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
    MemRead,
    MemWrite,
    Module,
    Mux,
    Parameter,
    PartSelect,
    Ref,
    Signal,
    Slice,
    SubmoduleInst,
    SwitchNode,
    UnaryOp,
    _subst_genvar_in_stmt,
)


# -----------------------------------------------------------------
# JITModule
# -----------------------------------------------------------------
class JITModule:
    """Flat, compiled module for cycle-accurate simulation."""

    def __init__(
        self,
        module: Module,
        use_xz: bool = False,
        param_overrides: Optional[Dict[str, Any]] = None,
    ):
        if use_xz:
            raise NotImplementedError("JIT mode does not support X/Z simulation")

        self.use_xz = False
        self.param_overrides: Dict[str, Any] = dict(param_overrides) if param_overrides else {}

        # --- signal tables -------------------------------------------------
        self.sig_names: List[str] = []          # idx -> hierarchical name
        self.sig_widths: List[int] = []         # idx -> width
        self.sig_masks: List[int] = []          # idx -> (1<<width)-1
        self.sig_idx: Dict[str, int] = {}       # hierarchical name -> idx
        self._sig_obj_to_idx: Dict[int, int] = {}  # id(Signal) -> idx

        # --- memory tables -------------------------------------------------
        self.mem_names: List[str] = []
        self.mem_idx: Dict[str, int] = {}       # hierarchical name -> idx
        self.memories: List[List[int]] = []     # idx -> list of values
        self.mem_widths: List[int] = []
        self.mem_masks: List[int] = []

        # --- array tables --------------------------------------------------
        self.arr_names: List[str] = []
        self.arr_idx: Dict[str, int] = {}
        self.arrays: List[Dict[int, int]] = []
        self.arr_widths: List[int] = []
        self.arr_masks: List[int] = []

        # --- compiled functions --------------------------------------------
        self.comb_fns: List[Callable[[], None]] = []
        self.seq_fns: List[Callable[[], None]] = []

        # --- state ---------------------------------------------------------
        self.state: List[int] = []
        self.next_state: List[int] = []

        self._compile(module)

    # -----------------------------------------------------------------
    # Compilation
    # -----------------------------------------------------------------
    def _compile(self, module: Module):
        self._collect_signals(module, "")
        self._init_state()
        self._compile_module(module, "")

    def _collect_signals(self, mod: Module, prefix: str):
        """Recursively collect all signals, memories, arrays."""
        for name, sig in list(mod._inputs.items()) + list(mod._outputs.items()) + \
                         list(mod._wires.items()) + list(mod._regs.items()):
            flat_name = prefix + name
            idx = len(self.sig_names)
            self.sig_names.append(flat_name)
            self.sig_widths.append(sig.width)
            mask = (1 << sig.width) - 1
            self.sig_masks.append(mask)
            self.sig_idx[flat_name] = idx
            self._sig_obj_to_idx[id(sig)] = idx

        for name, mem in mod._memories.items():
            flat_name = prefix + name
            idx = len(self.memories)
            self.mem_names.append(flat_name)
            self.mem_idx[flat_name] = idx
            self.memories.append([0] * mem.depth)
            self.mem_widths.append(mem.width)
            self.mem_masks.append((1 << mem.width) - 1)

        for name, arr in mod._arrays.items():
            flat_name = prefix + name
            idx = len(self.arrays)
            self.arr_names.append(flat_name)
            self.arr_idx[flat_name] = idx
            self.arrays.append({i: 0 for i in range(arr.depth)})
            self.arr_widths.append(arr.width)
            self.arr_masks.append((1 << arr.width) - 1)

        # implicit submodules
        for inst_name, submod in mod._submodules:
            self._collect_signals(submod, prefix + inst_name + "_")

        # explicit SubmoduleInst inside statements
        def _scan(stmts):
            for stmt in stmts:
                if isinstance(stmt, SubmoduleInst):
                    self._collect_signals(stmt.module, prefix + stmt.name + "_")
                elif isinstance(stmt, (IfNode, GenIfNode)):
                    _scan(stmt.then_body)
                    _scan(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, body in stmt.cases:
                        _scan(body)
                    _scan(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    for i in range(stmt.start, stmt.end):
                        unrolled = [_subst_genvar_in_stmt(s, stmt.var_name, i) for s in stmt.body]
                        _scan(unrolled)

        _scan(mod._top_level)
        for body in mod._comb_blocks:
            _scan(body)
        for _, _, _, _, body in mod._seq_blocks:
            _scan(body)

    def _init_state(self):
        self.state = [0] * len(self.sig_names)
        self.next_state = [0] * len(self.sig_names)

    def _reset_next_state(self):
        """Copy current state into next_state so only explicitly written signals change on commit."""
        self.next_state = self.state.copy()

    def _get_sig_idx(self, sig: Signal) -> int:
        idx = self._sig_obj_to_idx.get(id(sig))
        if idx is None:
            raise ValueError(f"JIT: unknown signal {sig} (name={sig.name})")
        return idx

    def _get_mem_idx(self, name: str, prefix: str) -> int:
        full = prefix + name
        idx = self.mem_idx.get(full)
        if idx is None:
            raise ValueError(f"JIT: unknown memory {full}")
        return idx

    def _get_arr_idx(self, name: str, prefix: str) -> int:
        full = prefix + name
        idx = self.arr_idx.get(full)
        if idx is None:
            raise ValueError(f"JIT: unknown array {full}")
        return idx

    def _compile_module(self, mod: Module, prefix: str):
        """Compile top-level, comb and seq statements of *mod*."""
        # top_level
        for stmt in mod._top_level:
            fn = self._compile_stmt(stmt, prefix, mode="comb")
            if fn:
                self.comb_fns.append(fn)

        # comb blocks
        for body in mod._comb_blocks:
            for stmt in body:
                fn = self._compile_stmt(stmt, prefix, mode="comb")
                if fn:
                    self.comb_fns.append(fn)

        # seq blocks
        for _, _, _, _, body in mod._seq_blocks:
            for stmt in body:
                fn = self._compile_stmt(stmt, prefix, mode="seq")
                if fn:
                    self.seq_fns.append(fn)

        # implicit port connections for submodules
        for inst_name, submod in mod._submodules:
            child_prefix = prefix + inst_name + "_"
            for pname in list(submod._inputs.keys()) + list(submod._outputs.keys()):
                if hasattr(mod, pname):
                    parent_sig = getattr(mod, pname)
                    if isinstance(parent_sig, Signal):
                        child_sig = getattr(submod, pname)
                        if pname in submod._inputs:
                            # parent drives child input
                            assign = Assign(child_sig, parent_sig._expr, blocking=True)
                            fn = self._compile_stmt(assign, child_prefix, mode="comb")
                            if fn:
                                self.comb_fns.append(fn)
                        elif pname in submod._outputs:
                            # child output drives parent: skip if parent already driven
                            if getattr(parent_sig, '_driven_by', None) is not None:
                                continue
                            assign = Assign(parent_sig, child_sig._expr, blocking=True)
                            fn = self._compile_stmt(assign, prefix, mode="comb")
                            if fn:
                                self.comb_fns.append(fn)

        # recurse into implicit submodules
        for inst_name, submod in mod._submodules:
            self._compile_module(submod, prefix + inst_name + "_")

        # recurse into explicit SubmoduleInst inside statements
        def _recurse(stmts):
            for stmt in stmts:
                if isinstance(stmt, SubmoduleInst):
                    child_prefix = prefix + stmt.name + "_"
                    self._compile_module(stmt.module, child_prefix)
                    # Generate port connections from port_map
                    for port_name, expr in stmt.port_map.items():
                        child_sig = getattr(stmt.module, port_name, None)
                        if child_sig is None or not isinstance(child_sig, Signal):
                            continue
                        if port_name in stmt.module._inputs:
                            assign = Assign(child_sig, expr, blocking=True)
                            fn = self._compile_stmt(assign, child_prefix, mode="comb")
                            if fn:
                                self.comb_fns.append(fn)
                        elif port_name in stmt.module._outputs:
                            # expr may be a Signal; use its _expr for Assign value
                            from rtlgen.core import _to_expr
                            val_expr = _to_expr(expr) if isinstance(expr, Signal) else expr
                            assign = Assign(val_expr, child_sig._expr, blocking=True)
                            fn = self._compile_stmt(assign, prefix, mode="comb")
                            if fn:
                                self.comb_fns.append(fn)
                elif isinstance(stmt, (IfNode, GenIfNode)):
                    _recurse(stmt.then_body)
                    _recurse(stmt.else_body)
                elif isinstance(stmt, SwitchNode):
                    for _, body in stmt.cases:
                        _recurse(body)
                    _recurse(stmt.default_body)
                elif isinstance(stmt, ForGenNode):
                    for i in range(stmt.start, stmt.end):
                        unrolled = [_subst_genvar_in_stmt(s, stmt.var_name, i) for s in stmt.body]
                        _recurse(unrolled)

        _recurse(mod._top_level)
        for body in mod._comb_blocks:
            _recurse(body)
        for _, _, _, _, body in mod._seq_blocks:
            _recurse(body)

    # -----------------------------------------------------------------
    # Expression compiler
    # -----------------------------------------------------------------
    def _compile_expr(self, expr: Any, prefix: str) -> Callable[[], int]:
        if isinstance(expr, int):
            return lambda: expr
        if isinstance(expr, Const):
            return lambda: int(expr.value)
        if isinstance(expr, Signal):
            return self._compile_expr(expr._expr, prefix)
        if isinstance(expr, Ref):
            idx = self._get_sig_idx(expr.signal)
            return lambda: self.state[idx]
        if isinstance(expr, BinOp):
            l_fn = self._compile_expr(expr.lhs, prefix)
            r_fn = self._compile_expr(expr.rhs, prefix)
            op = expr.op
            # AST interpreter does not mask BinOp results in _eval_expr;
            # masking only happens in _exec_assign (target-width).
            if op == "+":
                return lambda: l_fn() + r_fn()
            if op == "-":
                return lambda: l_fn() - r_fn()
            if op == "*":
                return lambda: l_fn() * r_fn()
            if op == "&":
                return lambda: l_fn() & r_fn()
            if op == "|":
                return lambda: l_fn() | r_fn()
            if op == "^":
                return lambda: l_fn() ^ r_fn()
            if op == "==":
                return lambda: 1 if l_fn() == r_fn() else 0
            if op == "!=":
                return lambda: 1 if l_fn() != r_fn() else 0
            if op == "<":
                return lambda: 1 if l_fn() < r_fn() else 0
            if op == "<=":
                return lambda: 1 if l_fn() <= r_fn() else 0
            if op == ">":
                return lambda: 1 if l_fn() > r_fn() else 0
            if op == ">=":
                return lambda: 1 if l_fn() >= r_fn() else 0
            if op == "<<":
                return lambda: l_fn() << r_fn()
            if op == ">>":
                return lambda: l_fn() >> r_fn()
            if op == "%":
                return lambda: l_fn() % r_fn() if r_fn() != 0 else 0
            raise ValueError(f"JIT: unknown binary op {op}")
        if isinstance(expr, UnaryOp):
            v_fn = self._compile_expr(expr.operand, prefix)
            op = expr.op
            if op == "~":
                return lambda: ~v_fn()
            raise ValueError(f"JIT: unknown unary op {op}")
        if isinstance(expr, Slice):
            v_fn = self._compile_expr(expr.operand, prefix)
            lo = expr.lo
            w = expr.hi - lo + 1
            mask = (1 << w) - 1
            return lambda: (v_fn() >> lo) & mask
        if isinstance(expr, PartSelect):
            v_fn = self._compile_expr(expr.operand, prefix)
            off_fn = self._compile_expr(expr.offset, prefix)
            mask = (1 << expr.width) - 1
            return lambda: (v_fn() >> off_fn()) & mask
        if isinstance(expr, BitSelect):
            v_fn = self._compile_expr(expr.operand, prefix)
            idx_fn = self._compile_expr(expr.index, prefix)
            return lambda: (v_fn() >> idx_fn()) & 1
        if isinstance(expr, Concat):
            op_fns = [self._compile_expr(op, prefix) for op in expr.operands]
            # operands are stored LSB first in rtlgen
            def _concat():
                result = 0
                off = 0
                for fn in op_fns:
                    result |= (fn() & ((1 << fn.__closure__[0].cell_contents.width) - 1)) << off
                    off += fn.__closure__[0].cell_contents.width
                return result
            # Simpler: each operand already has correct width, just shift and OR
            def _concat_simple():
                result = 0
                off = 0
                for fn in op_fns:
                    val = fn()
                    # We need operand width - but we lost it. Let's recapture.
                    # Actually, operand width is in the expr object, not in fn.
                    # We need to store widths alongside fns.
                    pass
            # Better approach: precompute operand masks
            masks = []
            for op in expr.operands:
                masks.append((1 << op.width) - 1)
            def _concat_final():
                result = 0
                off = 0
                for fn, m in zip(op_fns, masks):
                    result |= (fn() & m) << off
                    off += m.bit_length()  # This equals width for power-of-2 masks... no
                return result
            # Actually, width = mask.bit_length() for non-zero mask. But for mask=1 (width=1), bit_length=1, OK.
            # For mask=0 (width=1, value=0), bit_length=0, but width is 1. Use op.width directly.
            widths = [op.width for op in expr.operands]
            def _concat():
                result = 0
                off = 0
                for fn, w in zip(reversed(op_fns), reversed(widths)):
                    result |= (fn() & ((1 << w) - 1)) << off
                    off += w
                return result
            return _concat
        if isinstance(expr, Mux):
            c_fn = self._compile_expr(expr.cond, prefix)
            t_fn = self._compile_expr(expr.true_expr, prefix)
            f_fn = self._compile_expr(expr.false_expr, prefix)
            return lambda: t_fn() if c_fn() else f_fn()
        if isinstance(expr, MemRead):
            mem_i = self._get_mem_idx(expr.mem_name, prefix)
            addr_fn = self._compile_expr(expr.addr, prefix)
            depth = len(self.memories[mem_i])
            return lambda: self.memories[mem_i][addr_fn() % depth]
        if isinstance(expr, ArrayRead):
            arr_i = self._get_arr_idx(expr.array_name, prefix)
            idx_fn = self._compile_expr(expr.index, prefix)
            mask = (1 << expr.width) - 1
            return lambda: self.arrays[arr_i].get(idx_fn(), 0) & mask
        if isinstance(expr, GenVar):
            raise RuntimeError("JIT: GenVar should have been substituted before compilation")
        raise TypeError(f"JIT: unsupported expression type {type(expr).__name__}")

    # -----------------------------------------------------------------
    # Statement compiler
    # -----------------------------------------------------------------
    def _compile_stmt(self, stmt: Any, prefix: str, mode: str = "comb") -> Optional[Callable[[], None]]:
        if isinstance(stmt, Assign):
            return self._compile_assign(stmt, prefix, mode)
        if isinstance(stmt, IndexedAssign):
            return self._compile_indexed_assign(stmt, prefix, mode)
        if isinstance(stmt, IfNode):
            return self._compile_if(stmt, prefix, mode)
        if isinstance(stmt, SwitchNode):
            return self._compile_switch(stmt, prefix, mode)
        if isinstance(stmt, ForGenNode):
            return self._compile_for_gen(stmt, prefix, mode)
        if isinstance(stmt, GenIfNode):
            return self._compile_gen_if(stmt, prefix, mode)
        if isinstance(stmt, MemWrite):
            return self._compile_mem_write(stmt, prefix)
        if isinstance(stmt, ArrayWrite):
            return self._compile_array_write(stmt, prefix)
        if isinstance(stmt, (SubmoduleInst, Comment)):
            return None
        # Unknown statement type
        raise TypeError(f"JIT: unsupported statement type {type(stmt).__name__}")

    def _compile_assign(self, stmt: Assign, prefix: str, mode: str) -> Callable[[], None]:
        val_fn = self._compile_expr(stmt.value, prefix)
        target = stmt.target
        # In comb mode, all assignments are immediate (like AST interpreter).
        # In seq mode, blocking=False means non-blocking (next_state).
        write_state = (mode == "comb") or stmt.blocking

        if isinstance(target, Signal):
            idx = self._get_sig_idx(target)
            mask = self.sig_masks[idx]
            if write_state:
                return lambda: self.state.__setitem__(idx, val_fn() & mask)
            else:
                return lambda: self.next_state.__setitem__(idx, val_fn() & mask)

        if isinstance(target, Slice):
            base_sig = target.operand.signal  # operand is Ref(Signal)
            base_idx = self._get_sig_idx(base_sig)
            lo = target.lo
            w = target.hi - lo + 1
            val_mask = (1 << w) - 1
            base_mask = self.sig_masks[base_idx]
            inv_mask = (~(val_mask << lo)) & base_mask
            def _rmw():
                self.state[base_idx] = (self.state[base_idx] & inv_mask) | ((val_fn() & val_mask) << lo)
            return _rmw

        if isinstance(target, PartSelect):
            base_sig = target.operand.signal
            base_idx = self._get_sig_idx(base_sig)
            off_fn = self._compile_expr(target.offset, prefix)
            w = target.width
            val_mask = (1 << w) - 1
            base_mask = self.sig_masks[base_idx]
            def _rmw():
                lo = off_fn()
                inv_mask = (~(val_mask << lo)) & base_mask
                self.state[base_idx] = (self.state[base_idx] & inv_mask) | ((val_fn() & val_mask) << lo)
            return _rmw

        raise TypeError(f"JIT: unsupported assign target {type(target).__name__}")

    def _compile_indexed_assign(self, stmt: IndexedAssign, prefix: str, mode: str) -> Callable[[], None]:
        idx = self._get_sig_idx(stmt.target_signal)
        width = stmt.target_signal.width
        mask = self.sig_masks[idx]
        bit_idx_fn = self._compile_expr(stmt.index, prefix)
        val_fn = self._compile_expr(stmt.value, prefix)
        write_state = (mode == "comb") or stmt.blocking

        def _write():
            bit = val_fn() & 1
            bidx = bit_idx_fn()
            if bit:
                new_val = self.state[idx] | (1 << bidx)
            else:
                new_val = self.state[idx] & ~(1 << bidx)
            if write_state:
                self.state[idx] = new_val & mask
            else:
                self.next_state[idx] = new_val & mask
        return _write

    def _compile_if(self, stmt: IfNode, prefix: str, mode: str) -> Callable[[], None]:
        cond_fn = self._compile_expr(stmt.cond, prefix)
        then_fns = [f for s in stmt.then_body if (f := self._compile_stmt(s, prefix, mode))]
        else_fns = [f for s in stmt.else_body if (f := self._compile_stmt(s, prefix, mode))]
        def _if():
            if cond_fn():
                for fn in then_fns:
                    fn()
            else:
                for fn in else_fns:
                    fn()
        return _if

    def _compile_switch(self, stmt: SwitchNode, prefix: str, mode: str) -> Callable[[], None]:
        expr_fn = self._compile_expr(stmt.expr, prefix)
        cases = []
        for val, body in stmt.cases:
            val_fn = self._compile_expr(val, prefix)
            body_fns = [f for s in body if (f := self._compile_stmt(s, prefix, mode))]
            cases.append((val_fn, body_fns))
        def_fns = [f for s in stmt.default_body if (f := self._compile_stmt(s, prefix, mode))]
        def _switch():
            v = expr_fn()
            for val_fn, body_fns in cases:
                if v == val_fn():
                    for fn in body_fns:
                        fn()
                    return
            for fn in def_fns:
                fn()
        return _switch

    def _compile_for_gen(self, stmt: ForGenNode, prefix: str, mode: str) -> Callable[[], None]:
        fns = []
        for i in range(stmt.start, stmt.end):
            unrolled = [_subst_genvar_in_stmt(s, stmt.var_name, i) for s in stmt.body]
            for s in unrolled:
                fn = self._compile_stmt(s, prefix, mode)
                if fn:
                    fns.append(fn)
        def _for():
            for fn in fns:
                fn()
        return _for

    def _compile_gen_if(self, stmt: GenIfNode, prefix: str, mode: str) -> Callable[[], None]:
        cond_fn = self._compile_expr(stmt.cond, prefix)
        then_fns = [f for s in stmt.then_body if (f := self._compile_stmt(s, prefix, mode))]
        else_fns = [f for s in stmt.else_body if (f := self._compile_stmt(s, prefix, mode))]
        def _gen_if():
            if cond_fn():
                for fn in then_fns:
                    fn()
            else:
                for fn in else_fns:
                    fn()
        return _gen_if

    def _compile_mem_write(self, stmt: MemWrite, prefix: str) -> Callable[[], None]:
        mem_i = self._get_mem_idx(stmt.mem_name, prefix)
        addr_fn = self._compile_expr(stmt.addr, prefix)
        val_fn = self._compile_expr(stmt.value, prefix)
        depth = len(self.memories[mem_i])
        def _write():
            self.memories[mem_i][addr_fn() % depth] = val_fn()
        return _write

    def _compile_array_write(self, stmt: ArrayWrite, prefix: str) -> Callable[[], None]:
        arr_i = self._get_arr_idx(stmt.array_name, prefix)
        idx_fn = self._compile_expr(stmt.index, prefix)
        val_fn = self._compile_expr(stmt.value, prefix)
        mask = self.arr_masks[arr_i]
        def _write():
            self.arrays[arr_i][idx_fn()] = val_fn() & mask
        return _write

    # -----------------------------------------------------------------
    # Simulation API
    # -----------------------------------------------------------------
    def set(self, name, value: int):
        if isinstance(name, Signal):
            name = name.name
        idx = self.sig_idx.get(name)
        if idx is not None:
            self.state[idx] = int(value) & self.sig_masks[idx]
            return
        raise KeyError(f"JIT: signal '{name}' not found")

    def get(self, name) -> int:
        if isinstance(name, Signal):
            name = name.name
        idx = self.sig_idx.get(name)
        if idx is not None:
            return self.state[idx]
        raise KeyError(f"JIT: signal '{name}' not found")

    def step(self):
        """Execute one clock cycle."""
        # 1. Evaluate combinational logic (iterate to convergence)
        for _ in range(100):
            old = self.state.copy()
            for fn in self.comb_fns:
                fn()
            if self.state == old:
                break

        # 2. Prepare next_state as copy of current state
        self._reset_next_state()

        # 3. Evaluate sequential logic
        for fn in self.seq_fns:
            fn()

        # 4. Commit registers (only indices that changed)
        for i in range(len(self.state)):
            if self.next_state[i] != self.state[i]:
                self.state[i] = self.next_state[i]

        # 5. Re-evaluate combinational (reg outputs may drive comb)
        for _ in range(100):
            old = self.state.copy()
            for fn in self.comb_fns:
                fn()
            if self.state == old:
                break
