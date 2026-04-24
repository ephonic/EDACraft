"""Scan rtlgen Module AST and extract visualization graph."""

from typing import List, Optional, Set, Dict, Any

from rtlgen.core import (
    Module,
    Signal,
    Input,
    Output,
    Reg,
    Wire,
    Assign,
    SubmoduleInst,
    IfNode,
    SwitchNode,
    ForGenNode,
    GenIfNode,
    Ref,
    Slice,
    BitSelect,
    Concat,
    Mux,
    BinOp,
    UnaryOp,
)
from rtlgen.viz.model import VizGraph, VizModule, VizPort, VizSignal


def _collect_stmts(stmts: List[Any]) -> List[Any]:
    """Flatten all statements from a container (recursively into If/Switch/For)."""
    result = []
    for stmt in stmts:
        result.append(stmt)
        if isinstance(stmt, IfNode):
            result.extend(_collect_stmts(stmt.then_body))
            result.extend(_collect_stmts(stmt.else_body))
        elif isinstance(stmt, SwitchNode):
            for _, body in stmt.cases:
                result.extend(_collect_stmts(body))
            result.extend(_collect_stmts(stmt.default_body))
        elif isinstance(stmt, ForGenNode):
            result.extend(_collect_stmts(stmt.body))
        elif isinstance(stmt, GenIfNode):
            result.extend(_collect_stmts(stmt.then_body))
            result.extend(_collect_stmts(stmt.else_body))
    return result


def _get_all_stmts(module: Module) -> List[Any]:
    """Collect all statements from a module's top-level, comb, and seq blocks."""
    stmts = list(module._top_level)
    for body in module._comb_blocks:
        stmts.extend(_collect_stmts(body))
    for _, _, _, _, body in module._seq_blocks:
        stmts.extend(_collect_stmts(body))
    return stmts


def _find_refs(expr) -> List[Ref]:
    """Recursively find all Ref nodes (or bare Signals that act like refs) in an expression."""
    refs = []
    if expr is None:
        return refs
    if isinstance(expr, Ref):
        refs.append(expr)
    elif isinstance(expr, Signal):
        # Bare signal used as a value (wrap it conceptually)
        refs.append(Ref(expr))
    elif isinstance(expr, (Slice, BitSelect)):
        refs.extend(_find_refs(expr.operand))
    elif hasattr(expr, 'operands'):
        for op in expr.operands:
            refs.extend(_find_refs(op))
    elif hasattr(expr, 'lhs'):
        refs.extend(_find_refs(expr.lhs))
        refs.extend(_find_refs(expr.rhs))
    elif hasattr(expr, 'operand'):
        refs.extend(_find_refs(expr.operand))
    elif hasattr(expr, 'true_expr'):
        refs.extend(_find_refs(expr.true_expr))
        refs.extend(_find_refs(expr.false_expr))
        refs.extend(_find_refs(expr.cond))
    return refs


def _extract_signal_name(expr) -> Optional[str]:
    """Extract the base signal name from an expression."""
    if isinstance(expr, Signal):
        return expr.name
    if isinstance(expr, Ref):
        return expr.signal.name if hasattr(expr.signal, 'name') else None
    if isinstance(expr, (Slice, BitSelect)):
        return _extract_signal_name(expr.operand)
    return None


def scan_module(module: Module, name: Optional[str] = None) -> VizGraph:
    """Scan a rtlgen Module and produce a VizGraph.

    Args:
        module: The rtlgen Module to scan.
        name: Optional graph name (defaults to module.name).

    Returns:
        VizGraph containing modules and signal connections.
    """
    graph = VizGraph(name=name or module.name)

    # ------------------------------------------------------------------
    # 1. Collect submodule instances
    # ------------------------------------------------------------------
    submodules: Dict[str, Module] = {}  # instance_name -> Module
    submodule_set: Set[str] = set()

    # Implicit submodules (self.sub = SubModule())
    for inst_name, submod in module._submodules:
        submodules[inst_name] = submod
        submodule_set.add(inst_name)

    # Explicit submodules (SubmoduleInst in statements)
    all_stmts = _get_all_stmts(module)
    for stmt in all_stmts:
        if isinstance(stmt, SubmoduleInst):
            if stmt.name not in submodules:
                submodules[stmt.name] = stmt.module
                submodule_set.add(stmt.name)

    # ------------------------------------------------------------------
    # 2. Build signal-to-port mapping
    # ------------------------------------------------------------------
    # Map signal object id -> (instance_name, port_name, direction)
    sig_to_port: Dict[int, tuple] = {}
    for inst_name, submod in submodules.items():
        for pname, psig in submod._inputs.items():
            sig_to_port[id(psig)] = (inst_name, pname, "input")
        for pname, psig in submod._outputs.items():
            sig_to_port[id(psig)] = (inst_name, pname, "output")

    # Map parent signal id -> signal_name
    parent_sigs: Dict[int, str] = {}
    for name, sig in {**module._inputs, **module._outputs, **module._wires, **module._regs}.items():
        parent_sigs[id(sig)] = name

    # ------------------------------------------------------------------
    # 3. Build VizModule for each submodule
    # ------------------------------------------------------------------
    for inst_name, submod in submodules.items():
        vm = VizModule(
            name=getattr(submod, '_type_name', submod.name),
            instance_name=inst_name,
        )
        for pname, psig in submod._inputs.items():
            vm.ports.append(VizPort(name=pname, direction="input", width=psig.width))
        for pname, psig in submod._outputs.items():
            vm.ports.append(VizPort(name=pname, direction="output", width=psig.width))
        for pname, pval in submod._params.items():
            vm.params[pname] = pval
        graph.modules.append(vm)

    # Also add the parent module itself as a node
    parent_mod = VizModule(
        name=module.name,
        instance_name="(top)",
    )
    for pname, psig in module._inputs.items():
        parent_mod.ports.append(VizPort(name=pname, direction="input", width=psig.width))
    for pname, psig in module._outputs.items():
        parent_mod.ports.append(VizPort(name=pname, direction="output", width=psig.width))
    graph.modules.append(parent_mod)

    # ------------------------------------------------------------------
    # 4. Extract connections from Assign statements
    # ------------------------------------------------------------------
    # Patterns:
    #   self.submodule.input <<= parent_expr  ->  parent -> submodule
    #   self.parent_sig <<= self.submodule.output  ->  submodule -> parent
    #   self.sub_a.output <<= self.sub_b.input  ->  sub_b -> sub_a

    seen_edges = set()  # dedup

    def add_edge(src_mod, src_port, dst_mod, dst_port, width=1):
        # Skip clock/reset edges to reduce visual clutter
        if src_port in ("clk", "rst_n") or dst_port in ("clk", "rst_n"):
            return
        key = (src_mod, src_port, dst_mod, dst_port)
        if key in seen_edges:
            return
        seen_edges.add(key)
        vs = VizSignal(
            name=f"{src_mod}.{src_port}->{dst_mod}.{dst_port}",
            src_module=src_mod,
            src_port=src_port,
            dst_module=dst_mod,
            dst_port=dst_port,
            width=width,
        )
        graph.signals.append(vs)

    for stmt in all_stmts:
        if not isinstance(stmt, Assign):
            continue

        # Determine target info
        target_ref = None
        target_parent_name = None
        if isinstance(stmt.target, Ref):
            sig_id = id(stmt.target.signal)
            if sig_id in sig_to_port:
                target_ref = sig_to_port[sig_id]
            elif sig_id in parent_sigs:
                target_parent_name = parent_sigs[sig_id]
        elif isinstance(stmt.target, Signal):
            sig_id = id(stmt.target)
            if sig_id in sig_to_port:
                target_ref = sig_to_port[sig_id]
            elif sig_id in parent_sigs:
                target_parent_name = parent_sigs[sig_id]
        elif isinstance(stmt.target, (Slice, BitSelect)):
            # Try to resolve the base signal of a sliced target
            base = _extract_signal_name(stmt.target)
            if base:
                for sig_id, name in parent_sigs.items():
                    if name == base:
                        target_parent_name = base
                        break

        # Find all submodule refs in value expression
        refs = _find_refs(stmt.value)
        src_submods = []
        src_parent = None
        for ref in refs:
            sig_id = id(ref.signal)
            if sig_id in sig_to_port:
                src_submods.append(sig_to_port[sig_id])
            elif sig_id in parent_sigs:
                src_parent = parent_sigs[sig_id]

        # Case 1: target is submodule input -> connection INTO submodule
        if target_ref and target_ref[2] == "input":
            dst_inst, dst_port, _ = target_ref
            if src_submods:
                # Submodule output -> Submodule input
                for src_inst, src_port, _ in src_submods:
                    add_edge(src_inst, src_port, dst_inst, dst_port)
            elif src_parent:
                # Parent signal -> Submodule input
                add_edge("(top)", src_parent, dst_inst, dst_port)

        # Case 2: target is parent signal -> submodule outputs driving parent
        if target_parent_name:
            for src_inst, src_port, direction in src_submods:
                if direction == "output":
                    add_edge(src_inst, src_port, "(top)", target_parent_name)

    return graph
