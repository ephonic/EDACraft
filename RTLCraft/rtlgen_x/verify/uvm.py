"""Verification collateral generation directly from the executable model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    ConstExpr,
    MaskExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    Signal,
    SignalRef,
    SimModule,
    UnaryExpr,
)
from rtlgen_x.verify.module_adapter import normalize_executable_module


@dataclass(frozen=True)
class VerificationPort:
    """One verification-facing port."""

    name: str
    width: int
    direction: str
    signed: bool = False


@dataclass(frozen=True)
class VerificationInterface:
    """Ordered port view exported for verification collateral generation."""

    module_name: str
    reset_signal: Optional[str]
    inputs: Tuple[VerificationPort, ...]
    outputs: Tuple[VerificationPort, ...]


@dataclass(frozen=True)
class GeneratedArtifact:
    """One generated collateral artifact."""

    path: str
    contents: str


@dataclass(frozen=True)
class UvmCollateral:
    """Generated verification collateral rooted in one executable model."""

    module_name: str
    package_name: str
    reference_model_class: str
    interface: VerificationInterface
    artifacts: Tuple[GeneratedArtifact, ...]

    def artifact_map(self) -> Dict[str, str]:
        return {artifact.path: artifact.contents for artifact in self.artifacts}


def describe_verification_interface(module: Any) -> VerificationInterface:
    """Return an ordered verification-facing interface view for a module."""

    module = normalize_executable_module(module)
    inputs = []
    outputs = []
    for signal in module.signals:
        if signal.kind == "input":
            inputs.append(
                VerificationPort(
                    name=signal.name,
                    width=signal.width,
                    direction="input",
                    signed=signal.signed,
                )
            )
    signal_map = module.signal_map()
    for name in module.outputs:
        signal = signal_map[name]
        outputs.append(
            VerificationPort(
                name=signal.name,
                width=signal.width,
                direction="output",
                signed=signal.signed,
            )
        )
    return VerificationInterface(
        module_name=module.name,
        reset_signal=module.reset_signal,
        inputs=tuple(inputs),
        outputs=tuple(outputs),
    )


def emit_python_reference_model(
    module: Any,
    *,
    class_name: Optional[str] = None,
) -> str:
    """Emit a Python reference model wrapper backed by the local interpreter."""

    module = normalize_executable_module(module)
    model_fn = f"build_{_snake_name(module.name)}_module"
    class_name = class_name or f"{_camel_name(module.name)}ReferenceModel"
    signals_src = ",\n".join(
        f"            {_render_signal(signal)},"
        for signal in module.signals
    )
    memories_src = ",\n".join(
        f"            {_render_memory(memory)},"
        for memory in module.memories
    )
    assignments_src = ",\n".join(
        f"            {_render_assignment(assignment)},"
        for assignment in module.assignments
    )
    memory_writes_src = ",\n".join(
        f"            {_render_memory_write(write)},"
        for write in module.memory_writes
    )
    outputs_src = ", ".join(repr(name) for name in module.outputs)
    reset_src = (
        f'reset_signal={module.reset_signal!r},'
        if module.reset_signal is not None
        else "reset_signal=None,"
    )
    outputs_post_state_src = (
        "outputs_post_state=True,"
        if module.outputs_post_state
        else "outputs_post_state=False,"
    )
    return (
        f'"""Generated Python reference model for "{module.name}"."""\n\n'
        "from typing import Dict, Mapping\n\n"
        "from rtlgen_x.sim import (\n"
        "    Assignment,\n"
        "    BinaryExpr,\n"
        "    ConstExpr,\n"
        "    MaskExpr,\n"
        "    Memory,\n"
        "    MemoryReadExpr,\n"
        "    MemoryWrite,\n"
        "    MuxExpr,\n"
        "    PythonSimulator,\n"
        "    Signal,\n"
        "    SignalRef,\n"
        "    SimModule,\n"
        "    UnaryExpr,\n"
        ")\n\n\n"
        f"def {model_fn}() -> SimModule:\n"
        "    return SimModule(\n"
        f"        name={module.name!r},\n"
        "        signals=(\n"
        f"{signals_src}\n"
        "        ),\n"
        "        memories=(\n"
        f"{memories_src}\n"
        "        ),\n"
        "        assignments=(\n"
        f"{assignments_src}\n"
        "        ),\n"
        "        memory_writes=(\n"
        f"{memory_writes_src}\n"
        "        ),\n"
        f"        outputs=({outputs_src},),\n"
        f"        {reset_src}\n"
        f"        {outputs_post_state_src}\n"
        "    )\n\n\n"
        f"class {class_name}:\n"
        '    """Transaction-friendly wrapper around the local executable model."""\n\n'
        "    def __init__(self) -> None:\n"
        f"        self._sim = PythonSimulator({model_fn}())\n\n"
        "    @property\n"
        "    def input_names(self):\n"
        "        return self._sim.input_names\n\n"
        "    @property\n"
        "    def output_names(self):\n"
        "        return self._sim.output_names\n\n"
        "    def reset(self) -> None:\n"
        "        self._sim.reset()\n\n"
        "    def predict(self, transaction: Mapping[str, int]) -> Dict[str, int]:\n"
        "        return self._sim.step(transaction)\n"
    )


def generate_uvm_collateral(
    module: Any,
    *,
    package_name: Optional[str] = None,
    class_prefix: Optional[str] = None,
    interface_name: Optional[str] = None,
    clock_name: str = "clk",
) -> UvmCollateral:
    """Generate UVM skeleton collateral and a Python reference-model bridge."""

    module = normalize_executable_module(module)
    interface = describe_verification_interface(module)
    stem = _snake_name(module.name)
    class_prefix = class_prefix or stem
    package_name = package_name or f"{stem}_uvm_pkg"
    interface_name = interface_name or f"{stem}_if"
    txn_class = f"{class_prefix}_txn"
    monitor_class = f"{class_prefix}_monitor"
    scoreboard_class = f"{class_prefix}_scoreboard"
    sequencer_class = f"{class_prefix}_sequencer"
    sequence_class = f"{class_prefix}_smoke_seq"
    driver_class = f"{class_prefix}_driver"
    agent_class = f"{class_prefix}_agent"
    env_class = f"{class_prefix}_env"
    test_class = f"{class_prefix}_test"
    reference_model_class = f"{_camel_name(module.name)}ReferenceModel"
    artifacts = (
        GeneratedArtifact(
            path=f"{interface_name}.sv",
            contents=_emit_interface_sv(interface, interface_name, clock_name),
        ),
        GeneratedArtifact(
            path=f"{txn_class}.sv",
            contents=_emit_sequence_item_sv(interface, txn_class, clock_name),
        ),
        GeneratedArtifact(
            path=f"{sequencer_class}.sv",
            contents=_emit_sequencer_sv(txn_class, sequencer_class),
        ),
        GeneratedArtifact(
            path=f"{sequence_class}.sv",
            contents=_emit_sequence_sv(interface, txn_class, sequencer_class, sequence_class, clock_name),
        ),
        GeneratedArtifact(
            path=f"{driver_class}.sv",
            contents=_emit_driver_sv(interface, interface_name, txn_class, driver_class, clock_name),
        ),
        GeneratedArtifact(
            path=f"{monitor_class}.sv",
            contents=_emit_monitor_sv(interface, interface_name, txn_class, monitor_class, clock_name),
        ),
        GeneratedArtifact(
            path=f"{agent_class}.sv",
            contents=_emit_agent_sv(
                interface_name,
                driver_class,
                monitor_class,
                sequencer_class,
                agent_class,
            ),
        ),
        GeneratedArtifact(
            path=f"{scoreboard_class}.sv",
            contents=_emit_scoreboard_sv(
                interface,
                txn_class,
                scoreboard_class,
                clock_name,
                f"{stem}_ref_model.py",
            ),
        ),
        GeneratedArtifact(
            path=f"{env_class}.sv",
            contents=_emit_env_sv(agent_class, scoreboard_class, env_class),
        ),
        GeneratedArtifact(
            path=f"{test_class}.sv",
            contents=_emit_test_sv(env_class, sequence_class, test_class),
        ),
        GeneratedArtifact(
            path=f"{package_name}.sv",
            contents=_emit_package_sv(
                package_name,
                interface_name,
                txn_class,
                sequencer_class,
                sequence_class,
                driver_class,
                monitor_class,
                agent_class,
                scoreboard_class,
                env_class,
                test_class,
            ),
        ),
        GeneratedArtifact(
            path=f"{stem}_ref_model.py",
            contents=emit_python_reference_model(
                module,
                class_name=reference_model_class,
            ),
        ),
        GeneratedArtifact(
            path=f"{stem}_dpi_bridge.py",
            contents=_emit_dpi_bridge_python(
                interface,
                reference_model_class,
                clock_name,
            ),
        ),
        GeneratedArtifact(
            path=f"{stem}_dpi_bridge.c",
            contents=_emit_dpi_bridge_c(interface, stem, clock_name),
        ),
    )
    return UvmCollateral(
        module_name=module.name,
        package_name=package_name,
        reference_model_class=reference_model_class,
        interface=interface,
        artifacts=artifacts,
    )


def write_uvm_collateral(collateral: UvmCollateral, output_dir: Path | str) -> Tuple[Path, ...]:
    """Materialize generated collateral under one output directory."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    written = []
    for artifact in collateral.artifacts:
        path = root / artifact.path
        path.write_text(artifact.contents, encoding="utf-8")
        written.append(path)
    return tuple(written)


def _render_signal(signal: Signal) -> str:
    parts = [
        repr(signal.name),
        f"width={signal.width}",
        f"kind={signal.kind!r}",
    ]
    if signal.signed:
        parts.append("signed=True")
    if signal.init:
        parts.append(f"init={signal.init}")
    return f"Signal({', '.join(parts)})"


def _render_memory(memory: Memory) -> str:
    parts = [
        repr(memory.name),
        f"width={memory.width}",
        f"depth={memory.depth}",
    ]
    if memory.init:
        parts.append(f"init={memory.init!r}")
    return f"Memory({', '.join(parts)})"


def _render_assignment(assignment: Assignment) -> str:
    if assignment.phase == "comb":
        return f"Assignment({assignment.target!r}, {_render_expr(assignment.expr)})"
    return (
        f"Assignment({assignment.target!r}, {_render_expr(assignment.expr)}, "
        f"phase={assignment.phase!r})"
    )


def _render_memory_write(write: MemoryWrite) -> str:
    args = [
        repr(write.memory),
        _render_expr(write.addr),
        _render_expr(write.value),
    ]
    if not (isinstance(write.enable, ConstExpr) and write.enable.value == 1 and write.enable.width == 1):
        args.append(f"enable={_render_expr(write.enable)}")
    return f"MemoryWrite({', '.join(args)})"


def _render_expr(expr) -> str:
    if isinstance(expr, ConstExpr):
        return f"ConstExpr(value={expr.value}, width={expr.width})"
    if isinstance(expr, SignalRef):
        return f"SignalRef({expr.name!r})"
    if isinstance(expr, MemoryReadExpr):
        return f"MemoryReadExpr({expr.memory!r}, {_render_expr(expr.addr)})"
    if isinstance(expr, MaskExpr):
        return f"MaskExpr({_render_expr(expr.value)}, width={expr.width})"
    if isinstance(expr, UnaryExpr):
        return f"UnaryExpr({expr.op!r}, {_render_expr(expr.value)})"
    if isinstance(expr, BinaryExpr):
        return f"BinaryExpr({expr.op!r}, {_render_expr(expr.lhs)}, {_render_expr(expr.rhs)})"
    if isinstance(expr, MuxExpr):
        return (
            "MuxExpr("
            f"{_render_expr(expr.cond)}, "
            f"{_render_expr(expr.when_true)}, "
            f"{_render_expr(expr.when_false)})"
        )
    raise TypeError(f"unsupported expression type: {type(expr)!r}")


def _emit_interface_sv(
    interface: VerificationInterface,
    interface_name: str,
    clock_name: str,
) -> str:
    port_lines = [
        f"  logic {_sv_width(port.width)}{port.name};"
        for port in interface.inputs + interface.outputs
        if port.name != clock_name
    ]
    body = "\n".join(port_lines)
    return (
        f"interface {interface_name}(input logic {clock_name});\n"
        f"{body}\n"
        "endinterface\n"
    )


def _emit_sequence_item_sv(
    interface: VerificationInterface,
    txn_class: str,
    clock_name: str,
) -> str:
    txn_ports = _transaction_ports(interface, clock_name)
    field_macros = "\n".join(
        f"    `uvm_field_int({port.name}, UVM_ALL_ON)"
        for port in txn_ports
    )
    declarations = "\n".join(
        _sv_transaction_decl(port)
        for port in txn_ports
    )
    return (
        f"class {txn_class} extends uvm_sequence_item;\n"
        f"  `uvm_object_utils_begin({txn_class})\n"
        f"{field_macros}\n"
        "  `uvm_object_utils_end\n\n"
        f"{declarations}\n\n"
        f"  function new(string name=\"{txn_class}\");\n"
        "    super.new(name);\n"
        "  endfunction\n"
        "endclass\n"
    )


def _emit_sequencer_sv(txn_class: str, sequencer_class: str) -> str:
    return (
        f"class {sequencer_class} extends uvm_sequencer #({txn_class});\n"
        f"  `uvm_component_utils({sequencer_class})\n\n"
        f"  function new(string name=\"{sequencer_class}\", uvm_component parent=null);\n"
        "    super.new(name, parent);\n"
        "  endfunction\n"
        "endclass\n"
    )


def _emit_sequence_sv(
    interface: VerificationInterface,
    txn_class: str,
    sequencer_class: str,
    sequence_class: str,
    clock_name: str,
) -> str:
    driven_ports = _transaction_inputs(interface, clock_name)
    if driven_ports:
        body = (
            "    repeat (32) begin\n"
            f"      {txn_class} req;\n"
            f"      req = {txn_class}::type_id::create(\"req\");\n"
            "      start_item(req);\n"
            "      if (!req.randomize()) begin\n"
            "        `uvm_fatal(\"SEQ\", \"Randomization failed\")\n"
            "      end\n"
            "      finish_item(req);\n"
            "    end\n"
        )
    else:
        body = (
            "    repeat (32) begin\n"
            f"      {txn_class} req;\n"
            f"      req = {txn_class}::type_id::create(\"req\");\n"
            "      start_item(req);\n"
            "      finish_item(req);\n"
            "    end\n"
        )
    return (
        f"class {sequence_class} extends uvm_sequence #({txn_class});\n"
        f"  `uvm_object_utils({sequence_class})\n"
        f"  `uvm_declare_p_sequencer({sequencer_class})\n\n"
        f"  function new(string name=\"{sequence_class}\");\n"
        "    super.new(name);\n"
        "  endfunction\n\n"
        "  task body();\n"
        f"{body}"
        "  endtask\n"
        "endclass\n"
    )


def _emit_driver_sv(
    interface: VerificationInterface,
    interface_name: str,
    txn_class: str,
    driver_class: str,
    clock_name: str,
) -> str:
    drive_lines = "\n".join(
        f"      vif.{port.name} <= req.{port.name};"
        for port in _transaction_inputs(interface, clock_name)
    )
    return (
        f"class {driver_class} extends uvm_driver #({txn_class});\n"
        f"  `uvm_component_utils({driver_class})\n\n"
        f"  virtual {interface_name} vif;\n\n"
        f"  function new(string name=\"{driver_class}\", uvm_component parent=null);\n"
        "    super.new(name, parent);\n"
        "  endfunction\n\n"
        "  task run_phase(uvm_phase phase);\n"
        f"    {txn_class} req;\n"
        "    forever begin\n"
        "      seq_item_port.get_next_item(req);\n"
        f"      @(posedge vif.{clock_name});\n"
        f"{drive_lines}\n"
        "      seq_item_port.item_done();\n"
        "    end\n"
        "  endtask\n"
        "endclass\n"
    )


def _emit_monitor_sv(
    interface: VerificationInterface,
    interface_name: str,
    txn_class: str,
    monitor_class: str,
    clock_name: str,
) -> str:
    sampling_lines = "\n".join(
        f"      txn.{port.name} = vif.{port.name};"
        for port in _transaction_ports(interface, clock_name)
    )
    return (
        f"class {monitor_class} extends uvm_component;\n"
        f"  `uvm_component_utils({monitor_class})\n\n"
        f"  virtual {interface_name} vif;\n"
        f"  uvm_analysis_port#({txn_class}) ap;\n\n"
        f"  function new(string name=\"{monitor_class}\", uvm_component parent=null);\n"
        "    super.new(name, parent);\n"
        "    ap = new(\"ap\", this);\n"
        "  endfunction\n\n"
        "  task run_phase(uvm_phase phase);\n"
        f"    {txn_class} txn;\n"
        "    forever begin\n"
        f"      @(posedge vif.{clock_name});\n"
        f"      txn = {txn_class}::type_id::create(\"txn\", this);\n"
        f"{sampling_lines}\n"
        "      ap.write(txn);\n"
        "    end\n"
        "  endtask\n"
        "endclass\n"
    )


def _emit_agent_sv(
    interface_name: str,
    driver_class: str,
    monitor_class: str,
    sequencer_class: str,
    agent_class: str,
) -> str:
    return (
        f"class {agent_class} extends uvm_agent;\n"
        f"  `uvm_component_utils({agent_class})\n\n"
        f"  virtual {interface_name} vif;\n"
        f"  {driver_class} driver;\n"
        f"  {monitor_class} monitor;\n"
        f"  {sequencer_class} sequencer;\n\n"
        f"  function new(string name=\"{agent_class}\", uvm_component parent=null);\n"
        "    super.new(name, parent);\n"
        "  endfunction\n\n"
        "  function void build_phase(uvm_phase phase);\n"
        "    super.build_phase(phase);\n"
        f"    driver = {driver_class}::type_id::create(\"driver\", this);\n"
        f"    monitor = {monitor_class}::type_id::create(\"monitor\", this);\n"
        f"    sequencer = {sequencer_class}::type_id::create(\"sequencer\", this);\n"
        f"    if (!uvm_config_db#(virtual {interface_name})::get(this, \"\", \"vif\", vif)) begin\n"
        "      `uvm_fatal(\"NOVIF\", \"virtual interface not provided\")\n"
        "    end\n"
        "    driver.vif = vif;\n"
        "    monitor.vif = vif;\n"
        "  endfunction\n\n"
        "  function void connect_phase(uvm_phase phase);\n"
        "    super.connect_phase(phase);\n"
        "    driver.seq_item_port.connect(sequencer.seq_item_export);\n"
        "  endfunction\n"
        "endclass\n"
    )


def _emit_scoreboard_sv(
    interface: VerificationInterface,
    txn_class: str,
    scoreboard_class: str,
    clock_name: str,
    reference_model_path: str,
) -> str:
    compare_lines = "\n".join(
        (
            f"    if (observed.{port.name} !== expected.{port.name}) begin\n"
            "      error_count++;\n"
            f"      `uvm_error(\"{scoreboard_class.upper()}\", "
            f"$sformatf(\"{port.name} mismatch exp=%0h act=%0h\", "
            f"expected.{port.name}, observed.{port.name}))\n"
            "    end"
        )
        for port in interface.outputs
    )
    input_comment = ", ".join(port.name for port in _transaction_inputs(interface, clock_name)) or "none"
    output_comment = ", ".join(port.name for port in interface.outputs) or "none"
    predict_assign_lines = "\n".join(
        f"    expected.{port.name} = predicted_{port.name};"
        for port in interface.outputs
    )
    predict_args = ", ".join(
        [f"observed.{port.name}" for port in _transaction_inputs(interface, clock_name)]
        + [f"predicted_{port.name}" for port in interface.outputs]
    )
    dpi_decl = (
        "  import \"DPI-C\" context function void rtlgen_x_predict(\n"
        f"    input string ref_model_path,\n{_sv_predict_dpi_ports(interface, clock_name)}\n"
        "  );\n\n"
    )
    return (
        f"class {scoreboard_class} extends uvm_component;\n"
        f"  `uvm_component_utils({scoreboard_class})\n\n"
        f"{dpi_decl}"
        f"  uvm_analysis_imp#({txn_class}, {scoreboard_class}) analysis_export;\n"
        "  int unsigned error_count;\n\n"
        f"  function new(string name=\"{scoreboard_class}\", uvm_component parent=null);\n"
        "    super.new(name, parent);\n"
        "    analysis_export = new(\"analysis_export\", this);\n"
        "  endfunction\n\n"
        f"  protected virtual function {txn_class} predict({txn_class} observed);\n"
        f"    {txn_class} expected;\n"
        f"{_sv_predict_locals(interface)}\n"
        f"    expected = {txn_class}::type_id::create(\"expected\");\n"
        f"    // Hook this DPI call to the generated Python reference model: {reference_model_path}.\n"
        f"    // Inputs passed into the predictor: {input_comment}. Outputs filled here: {output_comment}.\n"
        f"    rtlgen_x_predict({reference_model_path!r}, {predict_args});\n"
        f"{predict_assign_lines}\n"
        "    return expected;\n"
        "  endfunction\n\n"
        f"  function void write({txn_class} observed);\n"
        f"    {txn_class} expected;\n"
        "    expected = predict(observed);\n"
        f"{compare_lines}\n"
        "  endfunction\n"
        "endclass\n"
    )


def _emit_env_sv(
    agent_class: str,
    scoreboard_class: str,
    env_class: str,
) -> str:
    return (
        f"class {env_class} extends uvm_env;\n"
        f"  `uvm_component_utils({env_class})\n\n"
        f"  {agent_class} agent;\n"
        f"  {scoreboard_class} scoreboard;\n\n"
        f"  function new(string name=\"{env_class}\", uvm_component parent=null);\n"
        "    super.new(name, parent);\n"
        "  endfunction\n\n"
        "  function void build_phase(uvm_phase phase);\n"
        "    super.build_phase(phase);\n"
        f"    agent = {agent_class}::type_id::create(\"agent\", this);\n"
        f"    scoreboard = {scoreboard_class}::type_id::create(\"scoreboard\", this);\n"
        "  endfunction\n\n"
        "  function void connect_phase(uvm_phase phase);\n"
        "    super.connect_phase(phase);\n"
        "    agent.monitor.ap.connect(scoreboard.analysis_export);\n"
        "  endfunction\n"
        "endclass\n"
    )


def _emit_test_sv(env_class: str, sequence_class: str, test_class: str) -> str:
    return (
        f"class {test_class} extends uvm_test;\n"
        f"  `uvm_component_utils({test_class})\n\n"
        f"  {env_class} env;\n\n"
        f"  function new(string name=\"{test_class}\", uvm_component parent=null);\n"
        "    super.new(name, parent);\n"
        "  endfunction\n\n"
        "  function void build_phase(uvm_phase phase);\n"
        "    super.build_phase(phase);\n"
        f"    env = {env_class}::type_id::create(\"env\", this);\n"
        "  endfunction\n\n"
        "  task run_phase(uvm_phase phase);\n"
        f"    {sequence_class} seq;\n"
        "    phase.raise_objection(this);\n"
        f"    seq = {sequence_class}::type_id::create(\"seq\");\n"
        "    seq.start(env.agent.sequencer);\n"
        "    phase.drop_objection(this);\n"
        "  endtask\n"
        "endclass\n"
    )


def _emit_package_sv(
    package_name: str,
    interface_name: str,
    txn_class: str,
    sequencer_class: str,
    sequence_class: str,
    driver_class: str,
    monitor_class: str,
    agent_class: str,
    scoreboard_class: str,
    env_class: str,
    test_class: str,
) -> str:
    includes = "\n".join(
        f'  `include "{name}.sv"'
        for name in (
            txn_class,
            sequencer_class,
            sequence_class,
            driver_class,
            monitor_class,
            agent_class,
            scoreboard_class,
            env_class,
            test_class,
        )
    )
    return (
        f'`include "{interface_name}.sv"\n\n'
        f"package {package_name};\n"
        "  import uvm_pkg::*;\n"
        '  `include "uvm_macros.svh"\n\n'
        f"{includes}\n"
        "endpackage\n"
    )


def _sv_transaction_decl(port: VerificationPort) -> str:
    rand_prefix = "rand " if port.direction == "input" else ""
    return f"  {rand_prefix}bit {_sv_width(port.width)}{port.name};"


def _transaction_ports(
    interface: VerificationInterface,
    clock_name: str,
) -> Tuple[VerificationPort, ...]:
    return tuple(port for port in interface.inputs + interface.outputs if port.name != clock_name)


def _transaction_inputs(
    interface: VerificationInterface,
    clock_name: str,
) -> Tuple[VerificationPort, ...]:
    return tuple(port for port in interface.inputs if port.name != clock_name)


def _sv_predict_locals(interface: VerificationInterface) -> str:
    return "\n".join(
        f"    bit {_sv_width(port.width)}predicted_{port.name};"
        for port in interface.outputs
    )


def _sv_predict_dpi_ports(
    interface: VerificationInterface,
    clock_name: str,
) -> str:
    lines = [
        f"    input bit {_sv_width(port.width)}{port.name},"
        for port in _transaction_inputs(interface, clock_name)
    ]
    output_ports = list(interface.outputs)
    for idx, port in enumerate(output_ports):
        suffix = "," if idx + 1 < len(output_ports) else ""
        lines.append(
            f"    output bit {_sv_width(port.width)}predicted_{port.name}{suffix}"
        )
    return "\n".join(lines)


def _sv_width(width: int) -> str:
    if width == 1:
        return ""
    return f"[{width - 1}:0] "


def _emit_dpi_bridge_python(
    interface: VerificationInterface,
    reference_model_class: str,
    clock_name: str,
) -> str:
    input_names = tuple(port.name for port in _transaction_inputs(interface, clock_name))
    output_names = tuple(port.name for port in interface.outputs)
    return (
        f'"""Generated Python DPI helper for "{interface.module_name}"."""\n\n'
        "from __future__ import annotations\n\n"
        "import importlib.util\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        f"REFERENCE_MODEL_CLASS = {reference_model_class!r}\n"
        f"TRANSACTION_INPUTS = {input_names!r}\n"
        f"OUTPUT_NAMES = {output_names!r}\n"
        "MODEL_CACHE = {}\n\n"
        "def _resolve_ref_model_path(ref_model_path: str) -> Path:\n"
        "    path = Path(ref_model_path)\n"
        "    if path.is_absolute():\n"
        "        return path\n"
        "    return Path(__file__).resolve().parent / path\n\n"
        "def _load_reference_model(ref_model_path: str):\n"
        "    resolved = _resolve_ref_model_path(ref_model_path)\n"
        "    module_name = resolved.stem + \"_rtlgen_x_ref\"\n"
        "    spec = importlib.util.spec_from_file_location(module_name, resolved)\n"
        "    if spec is None or spec.loader is None:\n"
        "        raise ImportError(f\"unable to load reference model from {resolved}\")\n"
        "    module = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(module)\n"
        "    ref_cls = getattr(module, REFERENCE_MODEL_CLASS, None)\n"
        "    if ref_cls is None:\n"
        "        candidates = [\n"
        "            getattr(module, name)\n"
        "            for name in dir(module)\n"
        "            if name.endswith(\"ReferenceModel\")\n"
        "        ]\n"
        "        if not candidates:\n"
        "            raise AttributeError(\"no ReferenceModel class found in generated module\")\n"
        "        ref_cls = candidates[0]\n"
        "    return ref_cls()\n\n"
        "def get_reference_model(ref_model_path: str):\n"
        "    resolved = str(_resolve_ref_model_path(ref_model_path))\n"
        "    model = MODEL_CACHE.get(resolved)\n"
        "    if model is None:\n"
        "        model = _load_reference_model(resolved)\n"
        "        MODEL_CACHE[resolved] = model\n"
        "    return model\n\n"
        "def predict_flat(ref_model_path: str, *input_values: int):\n"
        "    if len(input_values) != len(TRANSACTION_INPUTS):\n"
        "        raise ValueError(\n"
        "            f\"expected {len(TRANSACTION_INPUTS)} inputs, got {len(input_values)}\"\n"
        "        )\n"
        "    model = get_reference_model(ref_model_path)\n"
        "    transaction = {name: 0 for name in getattr(model, \"input_names\", ())}\n"
        "    for idx, name in enumerate(TRANSACTION_INPUTS):\n"
        "        transaction[name] = int(input_values[idx])\n"
        "    outputs = model.predict(transaction)\n"
        "    return tuple(int(outputs[name]) for name in OUTPUT_NAMES)\n\n"
        "def main(argv=None) -> int:\n"
        "    args = sys.argv[1:] if argv is None else list(argv)\n"
        "    expected_args = 1 + len(TRANSACTION_INPUTS)\n"
        "    if len(args) != expected_args:\n"
        "        raise SystemExit(\n"
        "            f\"usage: {Path(__file__).name} <ref_model.py> \"\n"
        "            + \" \".join(TRANSACTION_INPUTS)\n"
        "        )\n"
        "    outputs = predict_flat(args[0], *(int(value, 0) for value in args[1:]))\n"
        "    print(\" \".join(str(value) for value in outputs))\n"
        "    return 0\n\n"
        "if __name__ == \"__main__\":\n"
        "    raise SystemExit(main())\n"
    )


def _emit_dpi_bridge_c(
    interface: VerificationInterface,
    stem: str,
    clock_name: str,
) -> str:
    inputs = _transaction_inputs(interface, clock_name)
    outputs = interface.outputs
    func_args = ",\n".join(
        ["    const char* ref_model_path"]
        + [f"    {_c_dpi_arg_decl(port, is_output=False)}" for port in inputs]
        + [f"    {_c_dpi_arg_decl(port, is_output=True)}" for port in outputs]
    )
    tuple_build = "\n".join(
        [
            "  args = PyTuple_New(%d);" % (1 + len(inputs)),
            "  if (args == NULL) {",
            "    PyErr_Print();",
            f"{_c_zero_outputs(outputs, '    ')}",
            "    return;",
            "  }",
            "  PyTuple_SET_ITEM(args, 0, PyUnicode_FromString(ref_model_path));",
        ]
        + [
            f"  PyTuple_SET_ITEM(args, {idx + 1}, PyLong_FromUnsignedLongLong({_c_input_to_u64(port)}));"
            for idx, port in enumerate(inputs)
        ]
    )
    result_parse = "\n".join(
        [
            "  if (result == NULL) {",
            "    PyErr_Print();",
            f"{_c_zero_outputs(outputs, '    ')}",
            "    return;",
            "  }",
            f"  if (!PySequence_Check(result) || PySequence_Size(result) != {len(outputs)}) {{",
            "    Py_DECREF(result);",
            f"{_c_zero_outputs(outputs, '  ')}",
            "    return;",
            "  }",
        ]
        + [
            f"  {_c_output_from_result(port, idx)}"
            for idx, port in enumerate(outputs)
        ]
    )
    return (
        f"/* Generated DPI bridge for {interface.module_name}. */\n\n"
        "#include <Python.h>\n"
        '#include "svdpi.h"\n'
        "#include <stdint.h>\n\n"
        f'#define RTLGEN_X_DPI_PY_MODULE "{stem}_dpi_bridge"\n'
        '#ifndef RTLGEN_X_DPI_MODULE_DIR\n'
        '#define RTLGEN_X_DPI_MODULE_DIR "."\n'
        "#endif\n\n"
        "static PyObject* rtlgen_x_bridge_module = NULL;\n"
        "static PyObject* rtlgen_x_predict_fn = NULL;\n\n"
        "static uint64_t rtlgen_x_u64_from_svbitvec(const svBitVecVal* value, unsigned words) {\n"
        "  uint64_t result = 0;\n"
        "  unsigned limit = words < 2 ? words : 2;\n"
        "  unsigned idx;\n"
        "  for (idx = 0; idx < limit; ++idx) {\n"
        "    result |= ((uint64_t)value[idx]) << (32u * idx);\n"
        "  }\n"
        "  return result;\n"
        "}\n\n"
        "static void rtlgen_x_u64_to_svbitvec(svBitVecVal* value, unsigned words, uint64_t raw) {\n"
        "  unsigned idx;\n"
        "  for (idx = 0; idx < words; ++idx) {\n"
        "    value[idx] = (svBitVecVal)((raw >> (32u * idx)) & 0xffffffffu);\n"
        "  }\n"
        "}\n\n"
        "static int rtlgen_x_init_bridge(void) {\n"
        "  PyObject* module_dir;\n"
        "  PyObject* sys_path;\n"
        "  PyObject* module_name;\n"
        "  if (!Py_IsInitialized()) {\n"
        "    Py_Initialize();\n"
        "  }\n"
        "  if (rtlgen_x_predict_fn != NULL) {\n"
        "    return 1;\n"
        "  }\n"
        "  sys_path = PySys_GetObject(\"path\");\n"
        "  module_dir = PyUnicode_FromString(RTLGEN_X_DPI_MODULE_DIR);\n"
        "  if (module_dir == NULL) {\n"
        "    PyErr_Print();\n"
        "    return 0;\n"
        "  }\n"
        "  if (PySequence_Contains(sys_path, module_dir) == 0) {\n"
        "    PyList_Append(sys_path, module_dir);\n"
        "  }\n"
        "  Py_DECREF(module_dir);\n"
        "  module_name = PyUnicode_FromString(RTLGEN_X_DPI_PY_MODULE);\n"
        "  if (module_name == NULL) {\n"
        "    PyErr_Print();\n"
        "    return 0;\n"
        "  }\n"
        "  rtlgen_x_bridge_module = PyImport_Import(module_name);\n"
        "  Py_DECREF(module_name);\n"
        "  if (rtlgen_x_bridge_module == NULL) {\n"
        "    PyErr_Print();\n"
        "    return 0;\n"
        "  }\n"
        "  rtlgen_x_predict_fn = PyObject_GetAttrString(rtlgen_x_bridge_module, \"predict_flat\");\n"
        "  if (rtlgen_x_predict_fn == NULL || !PyCallable_Check(rtlgen_x_predict_fn)) {\n"
        "    PyErr_Print();\n"
        "    return 0;\n"
        "  }\n"
        "  return 1;\n"
        "}\n\n"
        f"void rtlgen_x_predict(\n{func_args}\n) {{\n"
        "  PyObject* args;\n"
        "  PyObject* result;\n"
        "  if (!rtlgen_x_init_bridge()) {\n"
        f"{_c_zero_outputs(outputs, '    ')}"
        "    return;\n"
        "  }\n"
        f"{tuple_build}\n"
        "  result = PyObject_CallObject(rtlgen_x_predict_fn, args);\n"
        "  Py_DECREF(args);\n"
        f"{result_parse}\n"
        "  Py_DECREF(result);\n"
        "}\n"
    )


def _snake_name(name: str) -> str:
    chars = [c.lower() if c.isalnum() else "_" for c in name]
    cleaned = "".join(chars)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "module"


def _camel_name(name: str) -> str:
    parts = [part for part in _snake_name(name).split("_") if part]
    return "".join(part[:1].upper() + part[1:] for part in parts) or "Module"


def _c_dpi_arg_decl(port: VerificationPort, *, is_output: bool) -> str:
    if port.width == 1:
        return f"svBit{'*' if is_output else ''} {'predicted_' if is_output else ''}{port.name}"
    qualifier = "" if is_output else "const "
    pointer = "*" if is_output else "*"
    name = f"predicted_{port.name}" if is_output else port.name
    return f"{qualifier}svBitVecVal{pointer} {name}"


def _c_input_to_u64(port: VerificationPort) -> str:
    if port.width == 1:
        return f"(uint64_t){port.name}"
    return f"rtlgen_x_u64_from_svbitvec({port.name}, {_sv_word_count(port.width)})"


def _c_output_from_result(port: VerificationPort, idx: int) -> str:
    cast_value = (
        f"(uint64_t)PyLong_AsUnsignedLongLong(PySequence_GetItem(result, {idx}))"
    )
    if port.width == 1:
        return (
            f"  *predicted_{port.name} = (svBit)({cast_value} & 0x1u);"
        )
    return (
        f"  rtlgen_x_u64_to_svbitvec(predicted_{port.name}, {_sv_word_count(port.width)}, {cast_value});"
    )


def _c_zero_outputs(outputs: Sequence[VerificationPort], indent: str) -> str:
    return "".join(
        (
            f"{indent}*predicted_{port.name} = 0;\n"
            if port.width == 1
            else f"{indent}rtlgen_x_u64_to_svbitvec(predicted_{port.name}, {_sv_word_count(port.width)}, 0);\n"
        )
        for port in outputs
    )


def _sv_word_count(width: int) -> int:
    return (width + 31) // 32
