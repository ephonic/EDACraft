"""Verification collateral generation directly from the executable model."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

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


REFERENCE_RUNTIME_ARTIFACT = "rtlgen_x_ref_runtime.py"


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
    reset_active_low: bool
    inputs: Tuple[VerificationPort, ...]
    outputs: Tuple[VerificationPort, ...]


@dataclass(frozen=True)
class GeneratedArtifact:
    """One generated collateral artifact."""

    path: str
    contents: str


@dataclass(frozen=True)
class UvmSequenceStep:
    """One directed transaction for generated UVM collateral."""

    inputs: Mapping[str, int]
    label: Optional[str] = None


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


@dataclass(frozen=True)
class UvmRuntimeBundle:
    """Runnable UVM bundle with DUT/top/filelist helpers."""

    module_name: str
    package_name: str
    interface_name: str
    dut_module_name: str
    top_module_name: str
    test_name: str
    artifacts: Tuple[GeneratedArtifact, ...]

    def artifact_map(self) -> Dict[str, str]:
        return {artifact.path: artifact.contents for artifact in self.artifacts}


@dataclass(frozen=True)
class ReferenceModelSmokeReport:
    path: Path
    class_name: str
    inputs: Mapping[str, int]
    predicted: Mapping[str, int]
    batched_predicted: Tuple[Mapping[str, int], ...]


@dataclass(frozen=True)
class IverilogCollateralProbeReport:
    collateral_dir: Path
    interface_source: Path
    package_source: Path
    interface_compile_ok: bool
    package_compile_ok: bool
    interface_returncode: int
    package_returncode: int
    interface_stdout: str
    interface_stderr: str
    package_stdout: str
    package_stderr: str
    skipped_reason: Optional[str] = None

    @property
    def uvm_support_available(self) -> bool:
        return self.package_compile_ok and self.skipped_reason is None


def describe_verification_interface(module: Any) -> VerificationInterface:
    """Return an ordered verification-facing interface view for a module."""

    source_module = module
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
    reset_signal, reset_active_low = _infer_reset_behavior(source_module, tuple(inputs))
    return VerificationInterface(
        module_name=module.name,
        reset_signal=reset_signal,
        reset_active_low=reset_active_low,
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
    signals_src = _render_collection_block(
        f"            {_render_signal(signal)}"
        for signal in module.signals
    )
    memories_src = _render_collection_block(
        f"            {_render_memory(memory)}"
        for memory in module.memories
    )
    assignments_src = _render_collection_block(
        f"            {_render_assignment(assignment)}"
        for assignment in module.assignments
    )
    memory_writes_src = _render_collection_block(
        f"            {_render_memory_write(write)}"
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
        "from __future__ import annotations\n\n"
        "import importlib.util\n"
        "import sys\n"
        "from pathlib import Path\n"
        "from typing import Dict, Mapping\n\n"
        "def _load_runtime_module():\n"
        f"    runtime_path = Path(__file__).with_name({REFERENCE_RUNTIME_ARTIFACT!r})\n"
        "    module_name = runtime_path.stem + \"_rtlgen_x_runtime\"\n"
        "    module = sys.modules.get(module_name)\n"
        "    if module is not None:\n"
        "        return module\n"
        "    spec = importlib.util.spec_from_file_location(module_name, runtime_path)\n"
        "    if spec is None or spec.loader is None:\n"
        "        raise ImportError(f\"unable to load runtime from {runtime_path}\")\n"
        "    module = importlib.util.module_from_spec(spec)\n"
        "    sys.modules[module_name] = module\n"
        "    spec.loader.exec_module(module)\n"
        "    return module\n\n"
        "_runtime = _load_runtime_module()\n"
        "Assignment = _runtime.Assignment\n"
        "BinaryExpr = _runtime.BinaryExpr\n"
        "ConstExpr = _runtime.ConstExpr\n"
        "MaskExpr = _runtime.MaskExpr\n"
        "Memory = _runtime.Memory\n"
        "MemoryReadExpr = _runtime.MemoryReadExpr\n"
        "MemoryWrite = _runtime.MemoryWrite\n"
        "MuxExpr = _runtime.MuxExpr\n"
        "PythonSimulator = _runtime.PythonSimulator\n"
        "Signal = _runtime.Signal\n"
        "SignalRef = _runtime.SignalRef\n"
        "SimModule = _runtime.SimModule\n"
        "UnaryExpr = _runtime.UnaryExpr\n\n\n"
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
        "        return self._sim.step(transaction)\n\n"
        "    def predict_batch(self, transactions):\n"
        "        rows = [tuple(int(item.get(name, 0)) for name in self.input_names) for item in transactions]\n"
        "        return tuple(dict(row) for row in self._sim.run_batch(rows))\n"
    )


def generate_uvm_collateral(
    module: Any,
    *,
    package_name: Optional[str] = None,
    class_prefix: Optional[str] = None,
    interface_name: Optional[str] = None,
    clock_name: str = "clk",
    directed_sequence: Optional[Sequence[UvmSequenceStep | Mapping[str, int]]] = None,
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
            contents=_emit_sequence_sv(
                interface,
                txn_class,
                sequencer_class,
                sequence_class,
                clock_name,
                directed_sequence=directed_sequence,
            ),
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
                interface,
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
                clock_name,
            ),
        ),
        GeneratedArtifact(
            path=REFERENCE_RUNTIME_ARTIFACT,
            contents=_emit_reference_runtime_python(),
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


def generate_uvm_runtime_bundle(
    module: Any,
    *,
    package_name: Optional[str] = None,
    class_prefix: Optional[str] = None,
    interface_name: Optional[str] = None,
    clock_name: str = "clk",
    dut_module_name: Optional[str] = None,
    dut_source: Optional[str] = None,
    top_module_name: Optional[str] = None,
    test_name: Optional[str] = None,
    directed_sequence: Optional[Sequence[UvmSequenceStep | Mapping[str, int]]] = None,
) -> UvmRuntimeBundle:
    """Generate a runnable UVM bundle with DUT/top/filelist/run script."""

    executable = normalize_executable_module(module)
    collateral = generate_uvm_collateral(
        module,
        package_name=package_name,
        class_prefix=class_prefix,
        interface_name=interface_name,
        clock_name=clock_name,
        directed_sequence=directed_sequence,
    )
    input_names = {port.name for port in collateral.interface.inputs}
    if clock_name not in input_names:
        raise ValueError(f"clock signal '{clock_name}' not found in module inputs")

    stem = _snake_name(executable.name)
    interface_name = next(
        artifact.path[:-3]
        for artifact in collateral.artifacts
        if artifact.path.endswith("_if.sv")
    )
    test_name = test_name or f"{class_prefix or stem}_test"
    top_module_name = top_module_name or f"{stem}_top"
    if dut_source is None:
        dut_source = _emit_legacy_dut_sv(module)
        dut_module_name = dut_module_name or _infer_preferred_sv_module_name(dut_source, module, executable)
    else:
        dut_module_name = dut_module_name or executable.name
    dut_file_name = f"{stem}_dut.sv"
    top_file_name = f"{top_module_name}.sv"
    runtime_artifacts = (
        GeneratedArtifact(path=dut_file_name, contents=dut_source),
        GeneratedArtifact(
            path=top_file_name,
            contents=_emit_uvm_top_sv(
                collateral.interface,
                package_name=collateral.package_name,
                interface_name=interface_name,
                dut_module_name=dut_module_name,
                top_module_name=top_module_name,
                test_name=test_name,
                clock_name=clock_name,
            ),
        ),
        GeneratedArtifact(
            path="filelist.f",
            contents=_emit_vcs_filelist(collateral.package_name, dut_file_name, top_file_name),
        ),
        GeneratedArtifact(
            path="run_vcs.sh",
            contents=_emit_vcs_run_script(
                top_module_name=top_module_name,
                test_name=test_name,
                dpi_bridge_c=f"{stem}_dpi_bridge.c",
            ),
        ),
    )
    return UvmRuntimeBundle(
        module_name=executable.name,
        package_name=collateral.package_name,
        interface_name=interface_name,
        dut_module_name=dut_module_name,
        top_module_name=top_module_name,
        test_name=test_name,
        artifacts=collateral.artifacts + runtime_artifacts,
    )


def write_uvm_collateral(collateral: UvmCollateral, output_dir: Path | str) -> Tuple[Path, ...]:
    """Materialize generated collateral under one output directory."""

    return _write_generated_artifacts(collateral.artifacts, output_dir)


def write_uvm_runtime_bundle(
    bundle: UvmRuntimeBundle,
    output_dir: Path | str,
    *,
    include_runtime_package: bool = False,
) -> Tuple[Path, ...]:
    """Materialize one runnable UVM bundle and optionally vendor rtlgen_x."""

    written = list(_write_generated_artifacts(bundle.artifacts, output_dir))
    root = Path(output_dir)
    run_script = root / "run_vcs.sh"
    if run_script.exists():
        run_script.chmod(0o755)
    if include_runtime_package:
        package_root = Path(__file__).resolve().parents[1]
        shutil.copytree(
            package_root,
            root / "rtlgen_x",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
    return tuple(written)


def load_generated_reference_model(
    ref_model_path: Path | str,
    *,
    class_name: Optional[str] = None,
):
    """Load one generated Python reference model class from disk."""

    path = Path(ref_model_path)
    spec = importlib.util.spec_from_file_location(f"{path.stem}_rtlgen_x_generated_ref", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load generated reference model from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if class_name is not None:
        ref_cls = getattr(module, class_name, None)
        if ref_cls is None:
            raise AttributeError(f"reference model class '{class_name}' not found in {path}")
        return ref_cls()
    for name in dir(module):
        candidate = getattr(module, name)
        if name.endswith("ReferenceModel") and callable(candidate):
            return candidate()
    raise AttributeError(f"no ReferenceModel class found in {path}")


def smoke_test_generated_reference_model(
    ref_model_path: Path | str,
    *,
    inputs: Optional[Mapping[str, int]] = None,
    class_name: Optional[str] = None,
) -> ReferenceModelSmokeReport:
    """Load a generated reference model and execute scalar plus batch predictions."""

    model = load_generated_reference_model(ref_model_path, class_name=class_name)
    tx = {name: 0 for name in getattr(model, "input_names", ())}
    if inputs is not None:
        tx.update({name: int(value) for name, value in dict(inputs).items()})
    model.reset()
    predicted = dict(model.predict(tx))
    model.reset()
    batched_predicted = tuple(dict(row) for row in model.predict_batch((tx,)))
    return ReferenceModelSmokeReport(
        path=Path(ref_model_path),
        class_name=type(model).__name__,
        inputs=tx,
        predicted=predicted,
        batched_predicted=batched_predicted,
    )


def probe_iverilog_uvm_collateral(
    collateral: UvmCollateral,
    *,
    output_dir: Optional[Path | str] = None,
    iverilog_cmd: str = "iverilog",
) -> IverilogCollateralProbeReport:
    """Probe how far generated SV/UVM collateral can go under iverilog."""

    if shutil.which(iverilog_cmd) is None:
        root = Path(output_dir) if output_dir is not None else Path(".")
        stem = _snake_name(collateral.module_name)
        return IverilogCollateralProbeReport(
            collateral_dir=root,
            interface_source=root / f"{stem}_if.sv",
            package_source=root / f"{collateral.package_name}.sv",
            interface_compile_ok=False,
            package_compile_ok=False,
            interface_returncode=-1,
            package_returncode=-1,
            interface_stdout="",
            interface_stderr="",
            package_stdout="",
            package_stderr="",
            skipped_reason="iverilog",
        )

    temp_dir_obj = None
    if output_dir is None:
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="rtlgen_x_iverilog_probe_")
        root = Path(temp_dir_obj.name)
    else:
        root = Path(output_dir)
    try:
        write_uvm_collateral(collateral, root)
        interface_name = next(
            artifact.path for artifact in collateral.artifacts
            if artifact.path.endswith("_if.sv")
        )
        interface_path = root / interface_name
        package_path = root / f"{collateral.package_name}.sv"

        interface_proc = subprocess.run(
            [iverilog_cmd, "-g2012", "-o", str(root / "interface.vvp"), str(interface_path)],
            capture_output=True,
            text=True,
        )
        package_proc = subprocess.run(
            [iverilog_cmd, "-g2012", "-I", str(root), "-o", str(root / "package.vvp"), str(package_path)],
            capture_output=True,
            text=True,
        )
        return IverilogCollateralProbeReport(
            collateral_dir=root,
            interface_source=interface_path,
            package_source=package_path,
            interface_compile_ok=interface_proc.returncode == 0,
            package_compile_ok=package_proc.returncode == 0,
            interface_returncode=interface_proc.returncode,
            package_returncode=package_proc.returncode,
            interface_stdout=interface_proc.stdout,
            interface_stderr=interface_proc.stderr,
            package_stdout=package_proc.stdout,
            package_stderr=package_proc.stderr,
        )
    finally:
        if temp_dir_obj is not None:
            temp_dir_obj.cleanup()


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
    directed_sequence: Optional[Sequence[UvmSequenceStep | Mapping[str, int]]] = None,
) -> str:
    normalized_directed = _normalize_directed_sequence(directed_sequence)
    if normalized_directed:
        body = _emit_directed_sequence_body(
            interface,
            txn_class,
            normalized_directed,
            clock_name,
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
    driven_ports = _transaction_inputs(interface, clock_name)
    reset_name = interface.reset_signal
    semantic_constraints = _default_sequence_constraints(driven_ports, reset_name=reset_name)
    if driven_ports:
        if reset_name is not None and any(port.name == reset_name for port in driven_ports):
            reset_asserted = "1'b0" if interface.reset_active_low else "1'b1"
            reset_deasserted = "1'b1" if interface.reset_active_low else "1'b0"
            reset_constraint_lines = [f"{reset_name} == {reset_asserted};"] + semantic_constraints
            body_constraint_lines = [f"{reset_name} == {reset_deasserted};"] + semantic_constraints
            reset_constraint_block = " ".join(reset_constraint_lines)
            body_constraint_block = " ".join(body_constraint_lines)
            body = (
                "    repeat (2) begin\n"
                f"      {txn_class} req;\n"
                f"      req = {txn_class}::type_id::create(\"reset_req\");\n"
                "      start_item(req);\n"
                f"      if (!req.randomize() with {{ {reset_constraint_block} }}) begin\n"
                "        `uvm_fatal(\"SEQ\", \"Reset randomization failed\")\n"
                "      end\n"
                "      finish_item(req);\n"
                "    end\n"
                "    repeat (32) begin\n"
                f"      {txn_class} req;\n"
                f"      req = {txn_class}::type_id::create(\"req\");\n"
                "      start_item(req);\n"
                f"      if (!req.randomize() with {{ {body_constraint_block} }}) begin\n"
                "        `uvm_fatal(\"SEQ\", \"Randomization failed\")\n"
                "      end\n"
                "      finish_item(req);\n"
                "    end\n"
            )
        else:
            constraint_block = " ".join(semantic_constraints)
            randomize_line = (
                "      if (!req.randomize() with { "
                + constraint_block
                + " }) begin\n"
                if semantic_constraints
                else "      if (!req.randomize()) begin\n"
            )
            body = (
                "    repeat (32) begin\n"
                f"      {txn_class} req;\n"
                f"      req = {txn_class}::type_id::create(\"req\");\n"
                "      start_item(req);\n"
                f"{randomize_line}"
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


def _normalize_directed_sequence(
    directed_sequence: Optional[Sequence[UvmSequenceStep | Mapping[str, int]]],
) -> Tuple[UvmSequenceStep, ...]:
    if not directed_sequence:
        return ()
    steps = []
    for index, step in enumerate(directed_sequence):
        if isinstance(step, UvmSequenceStep):
            steps.append(step)
            continue
        if isinstance(step, Mapping):
            steps.append(UvmSequenceStep(inputs=dict(step), label=f"step_{index}"))
            continue
        raise TypeError("directed_sequence entries must be mappings or UvmSequenceStep")
    return tuple(steps)


def _emit_directed_sequence_body(
    interface: VerificationInterface,
    txn_class: str,
    directed_sequence: Sequence[UvmSequenceStep],
    clock_name: str,
) -> str:
    driven_ports = _transaction_inputs(interface, clock_name)
    driven_names = {port.name for port in driven_ports}
    body_lines = []
    for index, step in enumerate(directed_sequence):
        unknown = sorted(set(step.inputs) - driven_names)
        if unknown:
            joined = ", ".join(unknown)
            raise ValueError(f"directed UVM step references unknown driven ports: {joined}")
        instance_name = _sv_string_literal(step.label or f"step_{index}")
        body_lines.append(f"    {txn_class} req;")
        body_lines.append(f"    req = {txn_class}::type_id::create({instance_name});")
        body_lines.append("    start_item(req);")
        for port in driven_ports:
            value = int(step.inputs.get(port.name, 0))
            body_lines.append(f"    req.{port.name} = {_sv_literal(port.width, value=value)};")
        body_lines.append("    finish_item(req);")
        if index + 1 < len(directed_sequence):
            body_lines.append("")
    if body_lines and body_lines[-1] == "":
        body_lines.pop()
    return "\n".join(body_lines) + "\n"


def _default_sequence_constraints(
    ports: Sequence[VerificationPort],
    *,
    reset_name: Optional[str],
) -> list[str]:
    constraints = []
    for port in ports:
        if port.name == reset_name:
            continue
        lower = port.name.lower()
        if lower.endswith("_gnt") or lower.endswith("_valid") or lower.endswith("_ready"):
            constraints.append(f"{port.name} == {_sv_literal(port.width, all_ones=True)};")
        elif lower.endswith("_rdata") or lower == "rdata":
            constraints.append(f"{port.name} == {_sv_literal(port.width, value=0)};")
        elif lower.endswith("_err") or lower.endswith("_slverr") or lower.endswith("error"):
            constraints.append(f"{port.name} == {_sv_literal(port.width, value=0)};")
    return constraints


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
        f"      @(negedge vif.{clock_name});\n"
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
        "      #1step;\n"
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
    return (
        f"class {scoreboard_class} extends uvm_component;\n"
        f"  `uvm_component_utils({scoreboard_class})\n\n"
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
        f"    rtlgen_x_predict({_sv_string_literal(reference_model_path)}, {predict_args});\n"
        f"{predict_assign_lines}\n"
        "    return expected;\n"
        "  endfunction\n\n"
        f"  function void write({txn_class} observed);\n"
        f"    {txn_class} expected;\n"
        "    expected = predict(observed);\n"
        f"{compare_lines}\n"
        "  endfunction\n"
        "\n"
        "  function void report_phase(uvm_phase phase);\n"
        "    super.report_phase(phase);\n"
        "    if (error_count != 0) begin\n"
        f"      `uvm_fatal(\"{scoreboard_class.upper()}\", $sformatf(\"observed %0d mismatches\", error_count))\n"
        "    end\n"
        f"    `uvm_info(\"{scoreboard_class.upper()}\", \"scoreboard passed\", UVM_LOW)\n"
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
    interface: VerificationInterface,
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
    clock_name: str,
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
    dpi_import_decl = _emit_scoreboard_dpi_import_sv(interface, clock_name)
    return (
        f'`include "{interface_name}.sv"\n\n'
        f"package {package_name};\n"
        "  import uvm_pkg::*;\n"
        '  `include "uvm_macros.svh"\n\n'
        f"{dpi_import_decl}\n"
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


def _emit_scoreboard_dpi_import_sv(
    interface: VerificationInterface,
    clock_name: str,
) -> str:
    return (
        "  import \"DPI-C\" context function void rtlgen_x_predict(\n"
        f"    input string ref_model_path,\n{_sv_predict_dpi_ports(interface, clock_name)}\n"
        "  );\n"
    )


def _sv_width(width: int) -> str:
    if width == 1:
        return ""
    return f"[{width - 1}:0] "


def _sv_string_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
    return f'"{escaped}"'


def _sv_literal(width: int, *, value: Optional[int] = None, all_ones: bool = False) -> str:
    if width <= 0:
        raise ValueError("width must be positive")
    if all_ones:
        value = (1 << width) - 1
    if value is None:
        raise ValueError("value or all_ones must be provided")
    if width == 1:
        return f"1'b{int(value) & 1}"
    return f"{width}'h{int(value) & ((1 << width) - 1):x}"


def _infer_reset_behavior(
    module: Any,
    inputs: Tuple[VerificationPort, ...],
) -> Tuple[Optional[str], bool]:
    reset_signal = getattr(module, "reset_signal", None)
    if reset_signal is not None:
        return reset_signal, False
    if hasattr(module, "_seq_blocks"):
        legacy_reset = _infer_legacy_reset_behavior(module)
        if legacy_reset is not None:
            return legacy_reset
    input_names = {port.name: port for port in inputs if port.width == 1}
    for candidate in ("rst", "reset", "rst_n", "reset_n"):
        if candidate in input_names:
            return candidate, False
    return None, False


def _infer_legacy_reset_behavior(module: Any) -> Optional[Tuple[str, bool]]:
    reset_name = None
    active_low = False
    for seq_item in getattr(module, "_seq_blocks", ()):
        if len(seq_item) < 2:
            continue
        inferred = _legacy_reset_expr_info(seq_item[1])
        if inferred is None:
            continue
        name, low = inferred
        if reset_name is None:
            reset_name = name
            active_low = low
            continue
        if reset_name != name or active_low != low:
            return None
    if reset_name is None:
        return None
    return reset_name, active_low


def _legacy_reset_expr_info(expr: Any) -> Optional[Tuple[str, bool]]:
    direct_name = getattr(expr, "name", None)
    if direct_name:
        return direct_name, False
    inner = getattr(expr, "_expr", None)
    if getattr(inner, "op", None) != "~":
        return None
    operand = getattr(inner, "operand", None)
    ref_signal = getattr(operand, "signal", None)
    ref_name = getattr(ref_signal, "name", None)
    if ref_name:
        return ref_name, True
    return None


def _emit_uvm_top_sv(
    interface: VerificationInterface,
    *,
    package_name: str,
    interface_name: str,
    dut_module_name: str,
    top_module_name: str,
    test_name: str,
    clock_name: str,
) -> str:
    driven_inputs = tuple(port for port in interface.inputs if port.name != clock_name)
    init_lines = "\n".join(f"    vif.{port.name} = '0;" for port in driven_inputs)
    port_lines = []
    for port in interface.inputs:
        if port.name == clock_name:
            port_lines.append(f"    .{port.name}(clk)")
        else:
            port_lines.append(f"    .{port.name}(vif.{port.name})")
    for port in interface.outputs:
        port_lines.append(f"    .{port.name}(vif.{port.name})")
    port_map = ",\n".join(port_lines)
    return (
        "`timescale 1ns/1ps\n\n"
        f"module {top_module_name};\n"
        "  import uvm_pkg::*;\n"
        f"  import {package_name}::*;\n\n"
        "  logic clk;\n"
        f"  {interface_name} vif(clk);\n\n"
        "  initial begin\n"
        "    clk = 1'b0;\n"
        f"{init_lines}\n"
        "  end\n\n"
        "  always #5 clk = ~clk;\n\n"
        f"  {dut_module_name} dut (\n"
        f"{port_map}\n"
        "  );\n\n"
        "  initial begin\n"
        f"    uvm_config_db#(virtual {interface_name})::set(null, \"*\", \"vif\", vif);\n"
        f"    run_test(\"{test_name}\");\n"
        "  end\n"
        "endmodule\n"
    )


def _emit_vcs_filelist(package_name: str, dut_file_name: str, top_file_name: str) -> str:
    return (
        f"{package_name}.sv\n"
        f"{dut_file_name}\n"
        f"{top_file_name}\n"
    )


def _emit_vcs_run_script(
    *,
    top_module_name: str,
    test_name: str,
    dpi_bridge_c: str,
) -> str:
    dpi_lib_stem = Path(dpi_bridge_c).stem
    return (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n\n"
        "export PYTHONPATH=\"$PWD${PYTHONPATH:+:$PYTHONPATH}\"\n"
        "VCS_BIN=\"${VCS_BIN:-$(command -v vcs)}\"\n"
        "if [ -z \"$VCS_BIN\" ]; then\n"
        "  echo \"vcs not found; source your simulator environment before running this script\" >&2\n"
        "  exit 1\n"
        "fi\n"
        "VCS_ROOT=\"$(cd \"$(dirname \"$VCS_BIN\")/../..\" && pwd)\"\n"
        "PYTHON_INCLUDES=\"$(python3-config --includes)\"\n"
        "if python3-config --embed --ldflags >/dev/null 2>&1; then\n"
        "  PYTHON_LDFLAGS=\"$(python3-config --embed --ldflags)\"\n"
        "else\n"
        "  PYTHON_LDFLAGS=\"$(python3-config --ldflags)\"\n"
        "fi\n\n"
        "rm -rf csrc simv simv.daidir ucli.key vc_hdrs.h "
        f"lib{dpi_lib_stem}.so\n"
        "gcc -shared -fPIC "
        "\"-I${VCS_ROOT}/include\" ${PYTHON_INCLUDES} "
        f"{dpi_bridge_c} ${{PYTHON_LDFLAGS}} "
        f"-o lib{dpi_lib_stem}.so\n"
        "vcs -full64 -sverilog -ntb_opts uvm-1.2 -timescale=1ns/1ps \\\n"
        "  +incdir+. -f filelist.f \\\n"
        "  -top "
        f"{top_module_name} \\\n"
        "  -o simv\n\n"
        "./simv -sv_lib "
        f"lib{dpi_lib_stem} "
        "+UVM_TESTNAME="
        f"{test_name}"
        " \"$@\"\n"
    )


def _emit_legacy_dut_sv(module: Any) -> str:
    if not (hasattr(module, "_inputs") and hasattr(module, "_outputs") and hasattr(module, "_seq_blocks")):
        raise ValueError("dut_source is required unless module is a legacy DSL module")
    emitter_cls = None
    profile_cls = None

    try:
        from rtlgen.core import Module as RtlgenModule
        from rtlgen.codegen import EmitProfile as RtlgenEmitProfile, VerilogEmitter as RtlgenVerilogEmitter

        if isinstance(module, RtlgenModule):
            emitter_cls = RtlgenVerilogEmitter
            profile_cls = RtlgenEmitProfile
    except ImportError:
        pass

    if emitter_cls is None or profile_cls is None:
        from rtlgen_x.dsl import EmitProfile as RtlgenXEmitProfile, VerilogEmitter as RtlgenXVerilogEmitter

        emitter_cls = RtlgenXVerilogEmitter
        profile_cls = RtlgenXEmitProfile

    emitter = emitter_cls(profile=profile_cls(language="systemverilog"))
    return emitter.emit_design(module)


def _write_generated_artifacts(
    artifacts: Sequence[GeneratedArtifact],
    output_dir: Path | str,
) -> Tuple[Path, ...]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    written = []
    for artifact in artifacts:
        path = root / artifact.path
        path.write_text(artifact.contents, encoding="utf-8")
        written.append(path)
    return tuple(written)


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
        "    sys.modules[module_name] = module\n"
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


def _emit_reference_runtime_python() -> str:
    return Path(__file__).with_name("ref_runtime.py").read_text(encoding="utf-8")


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
            f"  {{ PyObject* arg_{idx + 1} = {_c_input_to_pyobject(port)};"
            f" if (arg_{idx + 1} == NULL) {{ PyErr_Print(); Py_DECREF(args);"
            f" {_c_zero_outputs_inline(outputs)} return; }}"
            f" PyTuple_SET_ITEM(args, {idx + 1}, arg_{idx + 1}); }}"
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
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        "#include <stdint.h>\n\n"
        f'#define RTLGEN_X_DPI_PY_MODULE "{stem}_dpi_bridge"\n'
        '#ifndef RTLGEN_X_DPI_MODULE_DIR\n'
        '#define RTLGEN_X_DPI_MODULE_DIR "."\n'
        "#endif\n\n"
        "static PyObject* rtlgen_x_bridge_module = NULL;\n"
        "static PyObject* rtlgen_x_predict_fn = NULL;\n\n"
        "static PyObject* rtlgen_x_pyint_from_svbitvec(const svBitVecVal* value, unsigned words) {\n"
        "  size_t digits = ((size_t)words * 8u) + 1u;\n"
        "  char* buffer = (char*)malloc(digits);\n"
        "  char* cursor;\n"
        "  unsigned idx;\n"
        "  PyObject* py_value;\n"
        "  if (buffer == NULL) {\n"
        "    return PyErr_NoMemory();\n"
        "  }\n"
        "  cursor = buffer;\n"
        "  for (idx = words; idx > 0; --idx) {\n"
        "    snprintf(cursor, 9, \"%08x\", (unsigned)value[idx - 1]);\n"
        "    cursor += 8;\n"
        "  }\n"
        "  *cursor = '\\0';\n"
        "  py_value = PyLong_FromString(buffer, NULL, 16);\n"
        "  free(buffer);\n"
        "  return py_value;\n"
        "}\n\n"
        "static void rtlgen_x_zero_svbitvec(svBitVecVal* value, unsigned words) {\n"
        "  unsigned idx;\n"
        "  for (idx = 0; idx < words; ++idx) {\n"
        "    value[idx] = 0u;\n"
        "  }\n"
        "}\n\n"
        "static int rtlgen_x_svbitvec_from_pyint(svBitVecVal* value, unsigned words, PyObject* py_value) {\n"
        "  unsigned idx;\n"
        "  for (idx = 0; idx < words; ++idx) {\n"
        "    PyObject* shift = PyLong_FromUnsignedLong(32u * idx);\n"
        "    PyObject* shifted;\n"
        "    unsigned long chunk;\n"
        "    if (shift == NULL) {\n"
        "      PyErr_Print();\n"
        "      return 0;\n"
        "    }\n"
        "    shifted = PyNumber_Rshift(py_value, shift);\n"
        "    Py_DECREF(shift);\n"
        "    if (shifted == NULL) {\n"
        "      PyErr_Print();\n"
        "      return 0;\n"
        "    }\n"
        "    chunk = PyLong_AsUnsignedLongMask(shifted);\n"
        "    Py_DECREF(shifted);\n"
        "    if (PyErr_Occurred()) {\n"
        "      PyErr_Print();\n"
        "      return 0;\n"
        "    }\n"
        "    value[idx] = (svBitVecVal)(chunk & 0xffffffffu);\n"
        "  }\n"
        "  return 1;\n"
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


def _render_collection_block(lines: Sequence[str]) -> str:
    items = tuple(lines)
    if not items:
        return ""
    return ",\n".join(items) + ","


def _infer_sv_module_name(source: str) -> Optional[str]:
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped.startswith("module "):
            continue
        remainder = stripped[len("module ") :].strip()
        if not remainder:
            continue
        return remainder.split("(", 1)[0].strip()
    return None


def _infer_preferred_sv_module_name(source: str, module: Any, executable: SimModule) -> str:
    module_names = {
        line.strip()[len("module ") :].strip().split("(", 1)[0].strip()
        for line in source.splitlines()
        if line.strip().startswith("module ")
    }
    for candidate in (
        module.__class__.__name__,
        getattr(module, "_type_name", None),
        getattr(module, "name", None),
        executable.name,
    ):
        if candidate and candidate in module_names:
            return candidate
    return _infer_sv_module_name(source) or getattr(module, "_type_name", executable.name)


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


def _c_input_to_pyobject(port: VerificationPort) -> str:
    if port.width == 1:
        return f"PyLong_FromUnsignedLong((unsigned long)({port.name} & 0x1u))"
    return f"rtlgen_x_pyint_from_svbitvec({port.name}, {_sv_word_count(port.width)})"


def _c_output_from_result(port: VerificationPort, idx: int) -> str:
    if port.width == 1:
        return (
            f"{{ PyObject* item_{idx} = PySequence_GetItem(result, {idx}); "
            f"unsigned long raw_{idx}; "
            f"if (item_{idx} == NULL) {{ PyErr_Print(); {_c_zero_outputs_inline((port,))} return; }} "
            f"raw_{idx} = PyLong_AsUnsignedLongMask(item_{idx}); "
            f"Py_DECREF(item_{idx}); "
            f"if (PyErr_Occurred()) {{ PyErr_Print(); {_c_zero_outputs_inline((port,))} return; }} "
            f"*predicted_{port.name} = (svBit)(raw_{idx} & 0x1u); }}"
        )
    return (
        f"{{ PyObject* item_{idx} = PySequence_GetItem(result, {idx}); "
        f"if (item_{idx} == NULL) {{ PyErr_Print(); {_c_zero_outputs_inline((port,))} return; }} "
        f"if (!rtlgen_x_svbitvec_from_pyint(predicted_{port.name}, {_sv_word_count(port.width)}, item_{idx})) "
        f"{{ Py_DECREF(item_{idx}); {_c_zero_outputs_inline((port,))} return; }} "
        f"Py_DECREF(item_{idx}); }}"
    )


def _c_zero_outputs(outputs: Sequence[VerificationPort], indent: str) -> str:
    return "".join(
        (
            f"{indent}*predicted_{port.name} = 0;\n"
            if port.width == 1
            else f"{indent}rtlgen_x_zero_svbitvec(predicted_{port.name}, {_sv_word_count(port.width)});\n"
        )
        for port in outputs
    )


def _c_zero_outputs_inline(outputs: Sequence[VerificationPort]) -> str:
    return "".join(
        (
            f"*predicted_{port.name} = 0; "
            if port.width == 1
            else f"rtlgen_x_zero_svbitvec(predicted_{port.name}, {_sv_word_count(port.width)}); "
        )
        for port in outputs
    )


def _sv_word_count(width: int) -> int:
    return (width + 31) // 32
