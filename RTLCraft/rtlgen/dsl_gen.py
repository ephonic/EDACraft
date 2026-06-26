"""
rtlgen.dsl_gen — Deterministic SpecIR/ArchitectureIR -> RTLCraft DSL generator.

This module implements the first vertical slice of the spec-driven flow:

    SpecIR -> ArchitectureIR -> Module AST -> Simulator / VerilogEmitter

The generator intentionally focuses on a small, reliable subset:
  - combinational ALUs
  - simple register-update blocks
  - pipelined datapaths driven by structured OperationSpec stages
  - structural hierarchical wrappers with explicit submodule wiring
"""
from __future__ import annotations

import ast
import copy
import re
from typing import Any, Dict, List, Optional, Tuple

from rtlgen.core import Const, Input, Module, Output, Reg, Wire
from rtlgen.logic import Elif, Else, If, Switch
from rtlgen.spec_extractor import SpecCompleter
from rtlgen.spec_ir import ArchitectureIR, ConnectionSpec, OperationSpec, PortSpec, SpecIR, SubmoduleInstanceSpec


class DSLGenerator:
    """Generate a Module AST from SpecIR + ArchitectureIR."""

    def __init__(self, spec: SpecIR, arch: Optional[ArchitectureIR] = None):
        self.spec = SpecCompleter.complete(copy.deepcopy(spec))
        if arch is None:
            from rtlgen.arch_planner import ArchitecturePlanner

            self.arch = ArchitecturePlanner(self.spec).plan()
        else:
            self.arch = copy.deepcopy(arch)
        self._ports: List[PortSpec] = self._normalize_ports(self.spec.ports)

    def generate(self) -> Module:
        if self.arch.submodules or self.spec.category == "hierarchical":
            return self._generate_hierarchical()
        if self.arch.arch_type == "pipelined_datapath":
            return self._generate_stream_pipeline()
        if self.spec.category == "stream_pipeline":
            return self._generate_stream_pipeline()
        if self.spec.category == "register_update":
            return self._generate_register_update()
        if self.spec.category == "fsm_controller":
            return self._generate_fsm_controller()
        return self._generate_comb_alu()

    @staticmethod
    def supports(spec: SpecIR) -> bool:
        categories = {"comb_alu", "register_update", "fsm_controller", "stream_pipeline", "hierarchical"}
        return spec.category in categories

    def _generate_comb_alu(self) -> Module:
        module = self._create_module(include_seq=False)
        inputs = {p.name: getattr(module, p.name) for p in self._ports if p.direction == "input"}
        outputs = [p for p in self._ports if p.direction == "output"]
        output_signals = {p.name: getattr(module, p.name) for p in outputs}

        with module.comb:
            for port in outputs:
                output_signals[port.name] <<= Const(0, port.width)

            if self.spec.function.operations and self.spec.function.opcode_field:
                opcode_sig = inputs[self.spec.function.opcode_field]
                with Switch(opcode_sig) as sw:
                    for opcode, expr_text in self.spec.function.operations.items():
                        opcode_value = int(str(opcode), 0)
                        with sw.case(opcode_value):
                            out_name, rhs = self._split_assignment(expr_text)
                            if not out_name and outputs:
                                out_name = outputs[0].name
                            if out_name in output_signals:
                                output_signals[out_name] <<= self._expr_from_text(rhs, dict(inputs))
                    with sw.default():
                        for port in outputs:
                            output_signals[port.name] <<= Const(0, port.width)
            else:
                out_name, rhs = self._split_assignment(self.spec.function.expr)
                if not out_name and outputs:
                    out_name = outputs[0].name
                if out_name in output_signals:
                    output_signals[out_name] <<= self._expr_from_text(rhs, dict(inputs))

        return module

    def _generate_register_update(self) -> Module:
        module = self._create_module(include_seq=True)
        clk, rst_name, active_low = self._clock_and_reset(module)
        outputs = [p for p in self._ports if p.direction == "output"]
        output_signals = {p.name: getattr(module, p.name) for p in outputs}
        if not outputs:
            return module

        state_port = outputs[0]
        state_reg = self._add_signal(module, Reg, f"{state_port.name}_reg", state_port.width)
        env = {p.name: getattr(module, p.name) for p in self._ports if p.direction == "input"}
        env[state_port.name] = state_reg
        _, rhs = self._split_assignment(self.spec.function.expr)

        with module.comb:
            output_signals[state_port.name] <<= state_reg
            for port in outputs[1:]:
                output_signals[port.name] <<= Const(0, port.width)

        with module.seq(clk, getattr(module, rst_name), reset_active_low=active_low):
            with If(self._reset_condition(getattr(module, rst_name), active_low)):
                state_reg <<= Const(0, state_port.width)
            with Else():
                state_reg <<= self._expr_from_text(rhs, env) if rhs else state_reg

        return module

    def _generate_fsm_controller(self) -> Module:
        module = self._create_module(include_seq=True)
        clk, rst_name, active_low = self._clock_and_reset(module)
        state_reg = self._add_signal(module, Reg, "state_reg", 2)
        output_signals = {
            p.name: getattr(module, p.name)
            for p in self._ports
            if p.direction == "output"
        }

        with module.comb:
            for port in self._ports:
                if port.direction == "output":
                    output_signals[port.name] <<= Const(0, port.width)

        with module.seq(clk, getattr(module, rst_name), reset_active_low=active_low):
            with If(self._reset_condition(getattr(module, rst_name), active_low)):
                state_reg <<= Const(0, 2)
            with Else():
                state_reg <<= state_reg

        return module

    def _generate_stream_pipeline(self) -> Module:
        module = self._create_module(include_seq=True)
        clk, rst_name, active_low = self._clock_and_reset(module)
        input_env = {p.name: getattr(module, p.name) for p in self._ports if p.direction == "input"}
        output_signals = {
            p.name: getattr(module, p.name)
            for p in self._ports
            if p.direction == "output"
        }

        op_signals: Dict[Tuple[int, str], Wire] = {}
        reg_signals: Dict[str, Reg] = {}
        for stage in self.arch.stages:
            for op in stage.operation_specs:
                op_signals[(stage.stage_id, op.output)] = self._add_signal(
                    module, Wire, f"{stage.name}_{op.output}", op.width
                )
            for reg in stage.registers:
                reg_signals[reg.name] = self._add_signal(module, Reg, reg.name, reg.width)

        use_handshake = self._has_ready_valid_ports(module)
        valid_regs: List[Reg] = []
        pipe_stall: Optional[Wire] = None
        out_ready_sig = input_env.get("out_ready")
        if use_handshake:
            valid_regs = [
                self._add_signal(module, Reg, f"pipe_valid_{idx}", 1)
                for idx in range(max(len(self.arch.stages), 1))
            ]
            pipe_stall = self._add_signal(module, Wire, "pipe_stall", 1)

        stage_maps: Dict[int, Dict[str, Any]] = {}
        current_map: Dict[str, Any] = dict(input_env)

        with module.comb:
            for stage in self.arch.stages:
                stage_map = dict(current_map)
                for op in stage.operation_specs:
                    sig = op_signals[(stage.stage_id, op.output)]
                    sig <<= self._apply_operation(op, stage_map)
                    stage_map[op.output] = sig
                stage_maps[stage.stage_id] = stage_map

                next_map = dict(stage_map)
                for reg in stage.registers:
                    next_map[reg.source] = reg_signals[reg.name]
                current_map = next_map

            final_map = stage_maps[self.arch.stages[-1].stage_id] if self.arch.stages else dict(current_map)
            for port in self._ports:
                if port.direction != "output":
                    continue
                if port.name == "out_valid" and valid_regs:
                    output_signals[port.name] <<= valid_regs[-1]
                elif port.name == "in_ready" and valid_regs and out_ready_sig is not None:
                    output_signals[port.name] <<= ((valid_regs[-1] == 0) | (out_ready_sig == 1))
                elif port.name in final_map:
                    output_signals[port.name] <<= final_map[port.name]
                else:
                    output_signals[port.name] <<= Const(0, port.width)

            if pipe_stall is not None and out_ready_sig is not None:
                pipe_stall <<= (valid_regs[-1] == 1) & (out_ready_sig == 0)

        with module.seq(clk, getattr(module, rst_name), reset_active_low=active_low):
            with If(self._reset_condition(getattr(module, rst_name), active_low)):
                for reg in reg_signals.values():
                    reg <<= Const(0, reg.width)
                for reg in valid_regs:
                    reg <<= 0
            with Else():
                if pipe_stall is not None:
                    with If(pipe_stall == 0):
                        self._emit_pipeline_register_updates(stage_maps, reg_signals)
                        self._emit_valid_updates(valid_regs, getattr(module, "in_valid"))
                else:
                    self._emit_pipeline_register_updates(stage_maps, reg_signals)

        module._generated_spec_ir = self.spec.to_dict()
        module._generated_arch_ir = self.arch.to_dict()
        return module

    def _generate_hierarchical(self) -> Module:
        module = self._create_module(include_seq=False)
        self._ensure_clock_and_reset_ports(module)

        signal_env: Dict[str, Any] = {
            **{name: sig for name, sig in getattr(module, "_inputs", {}).items()},
            **{name: sig for name, sig in getattr(module, "_outputs", {}).items()},
        }
        for name in self._hierarchical_internal_signals(module):
            if name not in signal_env:
                signal_env[name] = self._add_signal(
                    module,
                    Wire,
                    name,
                    self._child_port_width(name),
                )

        route_bindings: Dict[str, Any] = {}
        route_targets: Dict[str, str] = {}

        for sm in self.arch.submodules:
            child = self._build_structural_child_module(sm)
            inst_name = sm.instance_name or sm.module_type or f"u_{len(route_targets)}"
            port_map: Dict[str, Any] = {}
            for port_name, mapped_name in sm.port_map.items():
                direction = self._infer_submodule_port_direction(inst_name, port_name, mapped_name)
                if direction == "output":
                    route_wire = self._add_signal(
                        module,
                        Wire,
                        f"{inst_name}_{port_name}",
                        self._child_port_width(mapped_name),
                    )
                    port_map[port_name] = route_wire
                    route_bindings[f"{inst_name}.{port_name}"] = route_wire
                    route_targets[f"{inst_name}.{port_name}"] = mapped_name
                elif mapped_name in signal_env:
                    port_map[port_name] = signal_env[mapped_name]
            module.instantiate(child, inst_name, port_map=port_map)

        for conn in self.arch.connections:
            src_sig = self._resolve_connection_endpoint(conn.source, route_bindings, signal_env)
            sink_name = self._endpoint_target_name(conn.sink)
            if src_sig is None or sink_name not in signal_env:
                continue
            route_bindings[conn.sink] = src_sig
            route_targets[conn.sink] = sink_name

        with module.comb:
            for output_port in (p for p in self._ports if p.direction == "output"):
                target = getattr(module, output_port.name)
                source = self._find_route_source(output_port.name, route_targets, route_bindings)
                if source is not None:
                    target <<= source
                else:
                    target <<= Const(0, output_port.width)

            for endpoint, sink_name in route_targets.items():
                if sink_name in getattr(module, "_outputs", {}):
                    continue
                sink_sig = signal_env.get(sink_name)
                src_sig = route_bindings.get(endpoint)
                if isinstance(sink_sig, Wire) and src_sig is not None:
                    sink_sig <<= src_sig

        module._generated_spec_ir = self.spec.to_dict()
        module._generated_arch_ir = self.arch.to_dict()
        return module

    def _emit_pipeline_register_updates(
        self,
        stage_maps: Dict[int, Dict[str, Any]],
        reg_signals: Dict[str, Reg],
    ) -> None:
        for stage in self.arch.stages:
            sources = stage_maps.get(stage.stage_id, {})
            for reg in stage.registers:
                reg_signals[reg.name] <<= sources[reg.source]

    @staticmethod
    def _emit_valid_updates(valid_regs: List[Reg], in_valid: Any) -> None:
        if not valid_regs:
            return
        valid_regs[0] <<= in_valid
        for idx in range(1, len(valid_regs)):
            valid_regs[idx] <<= valid_regs[idx - 1]

    def _apply_operation(self, op: OperationSpec, env: Dict[str, Any]) -> Any:
        values = [self._token_to_expr(token, env) for token in op.inputs]
        kind = op.kind
        if kind == "add":
            return values[0] + values[1]
        if kind == "sub":
            return values[0] - values[1]
        if kind == "mul":
            return values[0] * values[1]
        if kind == "and":
            return values[0] & values[1]
        if kind == "or":
            return values[0] | values[1]
        if kind == "xor":
            return values[0] ^ values[1]
        if kind == "shl":
            return values[0] << values[1]
        if kind == "shr":
            return values[0] >> values[1]
        if kind == "eq":
            return values[0] == values[1]
        if kind == "ne":
            return values[0] != values[1]
        if kind == "lt":
            return values[0] < values[1]
        if kind == "le":
            return values[0] <= values[1]
        if kind == "gt":
            return values[0] > values[1]
        if kind == "ge":
            return values[0] >= values[1]
        if kind == "not":
            return ~values[0]
        if kind == "neg":
            return -values[0]
        raise ValueError(f"Unsupported operation kind: {kind}")

    def _create_module(self, include_seq: bool) -> Module:
        module = Module(self.spec.name)
        module._type_name = self.spec.name
        for port in self._ports:
            cls = Input if port.direction == "input" else Output
            setattr(module, port.name, cls(port.width, port.name))
        if include_seq:
            self._ensure_clock_and_reset_ports(module)
        return module

    def _clock_and_reset(self, module: Module) -> tuple[Any, str, bool]:
        self._ensure_clock_and_reset_ports(module)
        rst_name = self._normalize_reset_name(self.spec.reset_name)
        return getattr(module, "clk"), rst_name, self._reset_is_active_low()

    def _ensure_clock_and_reset_ports(self, module: Module) -> None:
        if "clk" not in module._inputs:
            module.clk = Input(1, "clk")
        rst_name = self._normalize_reset_name(self.spec.reset_name)
        if rst_name not in module._inputs:
            setattr(module, rst_name, Input(1, rst_name))

    def _has_ready_valid_ports(self, module: Module) -> bool:
        needed = {"in_valid", "out_valid", "in_ready", "out_ready"}
        names = set(module._inputs) | set(module._outputs)
        return needed.issubset(names)

    def _reset_is_active_low(self) -> bool:
        return self.spec.reset_active == "low" or self.spec.reset_name.endswith("_n")

    @staticmethod
    def _reset_condition(reset_sig: Any, active_low: bool) -> Any:
        return reset_sig == 0 if active_low else reset_sig == 1

    def _token_to_expr(self, token: str, env: Dict[str, Any]) -> Any:
        if token in env:
            return env[token]
        try:
            return Const(int(token, 0), max(abs(int(token, 0)).bit_length() + (1 if int(token, 0) < 0 else 0), 1))
        except Exception as exc:
            raise KeyError(f"Unknown token '{token}' in generated architecture") from exc

    def _expr_from_text(self, expr_text: str, env: Dict[str, Any]) -> Any:
        expr_text = expr_text.strip()
        if not expr_text:
            return Const(0, 1)
        tree = ast.parse(expr_text, mode="eval")
        return self._expr_from_ast(tree.body, env)

    def _expr_from_ast(self, node: ast.AST, env: Dict[str, Any]) -> Any:
        if isinstance(node, ast.Name):
            return env[node.id]
        if isinstance(node, ast.Constant):
            value = int(node.value)
            return Const(value, max(abs(value).bit_length() + (1 if value < 0 else 0), 1))
        if isinstance(node, ast.UnaryOp):
            operand = self._expr_from_ast(node.operand, env)
            if isinstance(node.op, ast.Invert):
                return ~operand
            if isinstance(node.op, ast.USub):
                return -operand
            raise ValueError(f"Unsupported unary op: {type(node.op).__name__}")
        if isinstance(node, ast.BinOp):
            lhs = self._expr_from_ast(node.left, env)
            rhs = self._expr_from_ast(node.right, env)
            if isinstance(node.op, ast.Add):
                return lhs + rhs
            if isinstance(node.op, ast.Sub):
                return lhs - rhs
            if isinstance(node.op, ast.Mult):
                return lhs * rhs
            if isinstance(node.op, ast.BitAnd):
                return lhs & rhs
            if isinstance(node.op, ast.BitOr):
                return lhs | rhs
            if isinstance(node.op, ast.BitXor):
                return lhs ^ rhs
            if isinstance(node.op, ast.LShift):
                return lhs << rhs
            if isinstance(node.op, ast.RShift):
                return lhs >> rhs
            raise ValueError(f"Unsupported binary op: {type(node.op).__name__}")
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            lhs = self._expr_from_ast(node.left, env)
            rhs = self._expr_from_ast(node.comparators[0], env)
            op = node.ops[0]
            if isinstance(op, ast.Eq):
                return lhs == rhs
            if isinstance(op, ast.NotEq):
                return lhs != rhs
            if isinstance(op, ast.Lt):
                return lhs < rhs
            if isinstance(op, ast.LtE):
                return lhs <= rhs
            if isinstance(op, ast.Gt):
                return lhs > rhs
            if isinstance(op, ast.GtE):
                return lhs >= rhs
            raise ValueError(f"Unsupported compare op: {type(op).__name__}")
        raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

    @staticmethod
    def _split_assignment(expr: str) -> tuple[str, str]:
        if "=" in expr:
            lhs, rhs = expr.split("=", 1)
            return lhs.strip(), rhs.strip()
        return "", expr.strip()

    def _hierarchical_internal_signals(self, module: Module) -> List[str]:
        port_names = set(getattr(module, "_inputs", {})) | set(getattr(module, "_outputs", {}))
        names: List[str] = []
        for name in self.arch.signal_widths:
            if name not in port_names and name not in names:
                names.append(name)
        for conn in self.arch.connections:
            if conn.signal and conn.signal not in port_names and conn.signal not in names:
                names.append(conn.signal)
        for sm in self.arch.submodules:
            for mapped_name in sm.port_map.values():
                if mapped_name not in port_names and mapped_name not in names:
                    names.append(mapped_name)
        return names

    def _build_structural_child_module(self, sm: SubmoduleInstanceSpec) -> Module:
        child_name = f"{self.spec.name}_{sm.module_type or sm.instance_name or 'child'}"
        child = Module(child_name)
        child._type_name = child_name

        port_dirs = {
            port_name: self._infer_submodule_port_direction(sm.instance_name, port_name, mapped_name)
            for port_name, mapped_name in sm.port_map.items()
        }
        for port_name, mapped_name in sm.port_map.items():
            width = self._child_port_width(mapped_name)
            if port_dirs[port_name] == "output":
                setattr(child, port_name, Output(width, port_name))
            else:
                setattr(child, port_name, Input(width, port_name))

        output_ports = [name for name, direction in port_dirs.items() if direction == "output"]
        if output_ports:
            with child.comb:
                for port_name in output_ports:
                    out_sig = getattr(child, port_name)
                    paired_input = self._paired_input_name(port_name, list(sm.port_map))
                    if paired_input and paired_input in getattr(child, "_inputs", {}) and getattr(child, paired_input).width == out_sig.width:
                        out_sig <<= getattr(child, paired_input)
                    else:
                        out_sig <<= Const(0, out_sig.width)

        return child

    def _infer_submodule_port_direction(self, inst_name: str, port_name: str, mapped_name: str) -> str:
        lname = port_name.lower()
        if lname in {"clk", "clock", "rst", "reset", "rst_n", "reset_n", "aresetn"}:
            return "input"

        endpoint = f"{inst_name}.{port_name}" if inst_name else port_name
        for conn in self.arch.connections:
            if self._endpoint_matches(conn.source, endpoint):
                return "output"
            if self._endpoint_matches(conn.sink, endpoint):
                return "input"

        input_names = {p.name for p in self._ports if p.direction == "input"}
        output_names = {p.name for p in self._ports if p.direction == "output"}
        if mapped_name in input_names:
            return "input"
        if mapped_name in output_names:
            return "output"

        if lname.startswith(("out_", "o_")) or lname.endswith(("_out", "_o")):
            return "output"
        if lname.startswith(("in_", "i_")) or lname.endswith(("_in", "_i")):
            return "input"
        if any(token in lname for token in ("done", "result", "data_out")):
            return "output"
        return "input"

    @staticmethod
    def _endpoint_matches(endpoint: str, expected: str) -> bool:
        if endpoint == expected:
            return True
        if "." in endpoint and "." in expected:
            return endpoint.split(".", 1)[1] == expected.split(".", 1)[1]
        return False

    @staticmethod
    def _endpoint_target_name(endpoint: str) -> str:
        return endpoint.split(".", 1)[-1]

    @staticmethod
    def _find_route_source(target_name: str, route_targets: Dict[str, str], route_bindings: Dict[str, Any]) -> Optional[Any]:
        for endpoint, sink_name in route_targets.items():
            if sink_name == target_name and endpoint in route_bindings:
                return route_bindings[endpoint]
        return None

    @staticmethod
    def _resolve_connection_endpoint(
        endpoint: str,
        route_bindings: Dict[str, Any],
        signal_env: Dict[str, Any],
    ) -> Optional[Any]:
        if endpoint in route_bindings:
            return route_bindings[endpoint]
        bare = endpoint.split(".", 1)[-1]
        if bare in route_bindings:
            return route_bindings[bare]
        return signal_env.get(bare)

    def _child_port_width(self, mapped_name: str) -> int:
        if mapped_name in self.arch.signal_widths:
            return self.arch.signal_widths[mapped_name]
        for port in self._ports:
            if port.name == mapped_name:
                return port.width
        return 1

    @staticmethod
    def _paired_input_name(output_name: str, candidates: List[str]) -> Optional[str]:
        direct_pairs = [
            output_name.replace("out_", "in_", 1),
            output_name.replace("_out", "_in"),
            output_name.replace("result", "data", 1),
        ]
        for name in direct_pairs:
            if name in candidates:
                return name
        return None

    @staticmethod
    def _normalize_ports(ports: List[PortSpec]) -> List[PortSpec]:
        normalized: List[PortSpec] = []
        for port in ports:
            name, width = DSLGenerator._normalize_port_decl(port.name, port.width)
            normalized.append(PortSpec(
                name=name,
                direction=port.direction,
                width=width,
                signed=port.signed,
            ))
        return normalized

    @staticmethod
    def _normalize_port_decl(name: str, width: int) -> tuple[str, int]:
        match = re.fullmatch(r"([a-zA-Z_]\w*)(?:\[(\d+)(?::(\d+))?\])?", name)
        if match:
            base = match.group(1)
            hi = match.group(2)
            lo = match.group(3)
            if hi is not None:
                if lo is None:
                    width = 1
                else:
                    width = abs(int(hi) - int(lo)) + 1
            return base, width
        clean = re.sub(r"[^0-9a-zA-Z_]", "_", name).strip("_") or "sig"
        return clean, width

    def _normalize_reset_name(self, name: str) -> str:
        clean, _ = self._normalize_port_decl(name, 1)
        return clean or "rst"

    def _add_signal(self, module: Module, cls: Any, name: str, width: int) -> Any:
        clean = re.sub(r"[^0-9a-zA-Z_]", "_", name).strip("_") or "sig"
        candidate = clean
        suffix = 1
        while hasattr(module, candidate):
            candidate = f"{clean}_{suffix}"
            suffix += 1
        sig = cls(width, candidate)
        setattr(module, candidate, sig)
        return sig
