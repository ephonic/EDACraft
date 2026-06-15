"""L2 CycleIR tests for EarphoneRV32."""

from rtlgen import CycleContext

from earphone.modules.rv32.layer_L2_cycle.src.cycle import describe, rv32im_cycle_model


def test_describe_cycle_contract():
    info = describe()
    assert info["name"] == "EarphoneRV32"
    assert info["layer"] == "L2_cycle"
    assert info["status"] == "implemented"
    assert info["pipeline_stages"] == ["IF", "ID/EX", "WB"]
    assert info["div_latency_cycles"] == "32 (iterative)"


def test_reset_initializes_cycle_state():
    ctx = CycleContext(inputs={"rst_n": 0})
    rv32im_cycle_model()(ctx)

    assert ctx.state["pc"] == 0x1000
    assert ctx.state["fetch_valid"] == 0
    assert ctx.state["exec_valid"] == 0
    assert ctx.state["wb_valid"] == 0
    assert ctx.state["rf"] == [0] * 32


def test_fetch_advances_pc_and_exposes_icache_request():
    ctx = CycleContext(inputs={
        "rst_n": 1,
        "icache_valid": 1,
        "icache_rdata": 0x00000013,  # addi x0, x0, 0
        "dcache_valid": 1,
    })

    rv32im_cycle_model()(ctx)

    assert ctx.outputs["icache_req"] == 1
    assert ctx.outputs["icache_addr"] == 0x1000
    assert ctx.state["pc"] == 0x1004
    assert ctx.state["fetch_valid"] == 1
