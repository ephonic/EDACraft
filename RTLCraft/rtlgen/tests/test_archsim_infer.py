from rtlgen.archsim import (
    BehaviorSimulator,
    CalibrationTarget,
    calibrate_architecture_model,
    infer_architecture_from_module,
    infer_flow_from_module,
)
from rtlgen.sim import Assignment, BinaryExpr, Memory, MemoryReadExpr, MemoryWrite, Signal, SignalRef, SimModule


def _module():
    return SimModule(
        name="infer_mem_accum",
        signals=(
            Signal("we", width=1, kind="input"),
            Signal("addr", width=2, kind="input"),
            Signal("inp", width=8, kind="input"),
            Signal("acc", width=8, kind="state", init=1),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("acc"), MemoryReadExpr("mem", SignalRef("addr")))),
            Assignment("acc", BinaryExpr("+", SignalRef("acc"), SignalRef("inp")), phase="seq"),
        ),
        outputs=("out",),
        memories=(Memory("mem", width=8, depth=4, init=(1, 2, 3, 4)),),
        memory_writes=(MemoryWrite("mem", SignalRef("addr"), SignalRef("inp"), enable=SignalRef("we")),),
    )


def test_infer_architecture_and_flow_from_module():
    module = _module()
    model = infer_architecture_from_module(module)
    flow = infer_flow_from_module(module, tokens=6, bytes_per_token=16)

    assert "infer_mem_accum_compute" in model.stages
    assert flow.path[0].startswith("infer_mem_accum_")
    report = BehaviorSimulator().run(model, type("W", (), {"flows": (flow,)})())
    assert report.flow_metrics[flow.name].pipeline_latency >= 1


def test_calibrate_architecture_model_applies_overrides():
    module = _module()
    model = infer_architecture_from_module(module)
    calibrated = calibrate_architecture_model(
        model,
        (
            CalibrationTarget("infer_mem_accum_memory", latency=7, bandwidth_bytes_per_cycle=64),
            CalibrationTarget("infer_mem_accum_compute", initiation_interval=2),
        ),
    )

    assert calibrated.stage("infer_mem_accum_memory").latency == 7
    assert calibrated.stage("infer_mem_accum_memory").bandwidth_bytes_per_cycle == 64
    assert calibrated.stage("infer_mem_accum_compute").initiation_interval == 2
