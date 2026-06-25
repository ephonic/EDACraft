import pytest

from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    ClockDomain,
    ConstExpr,
    CppBackendScaffold,
    MaskExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    PythonSimulator,
    pack_signal_values_u64_words,
    pack_u64_words,
    Signal,
    SignalRef,
    SimModule,
    UnaryExpr,
)


def _accum_module() -> SimModule:
    return SimModule(
        name="python_accum",
        signals=(
            Signal("rst", width=1, kind="input"),
            Signal("inp", width=8, kind="input"),
            Signal("acc", width=8, kind="state", init=3),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("acc"), SignalRef("inp"))),
            Assignment("acc", SignalRef("out"), phase="seq"),
        ),
        outputs=("out",),
        reset_signal="rst",
    )


def _dual_clock_fifo_like_module() -> SimModule:
    return SimModule(
        name="python_dual_clock_fifo_like",
        signals=(
            Signal("wr_clk", width=1, kind="input"),
            Signal("rd_clk", width=1, kind="input"),
            Signal("wr_rst", width=1, kind="input"),
            Signal("rd_rst", width=1, kind="input"),
            Signal("wr_en", width=1, kind="input"),
            Signal("rd_en", width=1, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("wr_ptr", width=2, kind="state", init=0),
            Signal("rd_ptr", width=2, kind="state", init=0),
            Signal("rd_data", width=8, kind="state", init=0),
            Signal("dout", width=8, kind="output"),
        ),
        assignments=(
            Assignment("dout", SignalRef("rd_data")),
            Assignment(
                "wr_ptr",
                MuxExpr(SignalRef("wr_en"), BinaryExpr("+", SignalRef("wr_ptr"), ConstExpr(1, 2)), SignalRef("wr_ptr")),
                phase="seq",
                clock_domain="wr_clk",
            ),
            Assignment(
                "rd_ptr",
                MuxExpr(SignalRef("rd_en"), BinaryExpr("+", SignalRef("rd_ptr"), ConstExpr(1, 2)), SignalRef("rd_ptr")),
                phase="seq",
                clock_domain="rd_clk",
            ),
            Assignment(
                "rd_data",
                MuxExpr(SignalRef("rd_en"), MemoryReadExpr("fifo_mem", SignalRef("rd_ptr")), SignalRef("rd_data")),
                phase="seq",
                clock_domain="rd_clk",
            ),
        ),
        outputs=("dout",),
        memories=(Memory("fifo_mem", width=8, depth=4),),
        memory_writes=(
            MemoryWrite("fifo_mem", SignalRef("wr_ptr"), SignalRef("din"), enable=SignalRef("wr_en"), clock_domain="wr_clk"),
        ),
        clock_domains=(
            ClockDomain("wr_clk", reset_signal="wr_rst"),
            ClockDomain("rd_clk", reset_signal="rd_rst"),
        ),
        outputs_post_state=True,
    )


def _named_dual_clock_fifo_like_module() -> SimModule:
    return SimModule(
        name="python_named_dual_clock_fifo_like",
        signals=(
            Signal("wr_clk", width=1, kind="input"),
            Signal("rd_clk", width=1, kind="input"),
            Signal("wr_rst", width=1, kind="input"),
            Signal("rd_rst", width=1, kind="input"),
            Signal("wr_en", width=1, kind="input"),
            Signal("rd_en", width=1, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("wr_ptr", width=2, kind="state", init=0),
            Signal("rd_ptr", width=2, kind="state", init=0),
            Signal("rd_data", width=8, kind="state", init=0),
            Signal("dout", width=8, kind="output"),
        ),
        assignments=(
            Assignment("dout", SignalRef("rd_data")),
            Assignment(
                "wr_ptr",
                MuxExpr(SignalRef("wr_en"), BinaryExpr("+", SignalRef("wr_ptr"), ConstExpr(1, 2)), SignalRef("wr_ptr")),
                phase="seq",
                clock_domain="write",
            ),
            Assignment(
                "rd_ptr",
                MuxExpr(SignalRef("rd_en"), BinaryExpr("+", SignalRef("rd_ptr"), ConstExpr(1, 2)), SignalRef("rd_ptr")),
                phase="seq",
                clock_domain="read",
            ),
            Assignment(
                "rd_data",
                MuxExpr(SignalRef("rd_en"), MemoryReadExpr("fifo_mem", SignalRef("rd_ptr")), SignalRef("rd_data")),
                phase="seq",
                clock_domain="read",
            ),
        ),
        outputs=("dout",),
        memories=(Memory("fifo_mem", width=8, depth=4),),
        memory_writes=(
            MemoryWrite("fifo_mem", SignalRef("wr_ptr"), SignalRef("din"), enable=SignalRef("wr_en"), clock_domain="write"),
        ),
        clock_domains=(
            ClockDomain("write", clock_signal="wr_clk", reset_signal="wr_rst", aliases=("wr_clk",)),
            ClockDomain("read", clock_signal="rd_clk", reset_signal="rd_rst", aliases=("rd_clk",)),
        ),
        outputs_post_state=True,
    )


def test_python_reference_matches_compiled_scalar_and_batch(tmp_path):
    module = _accum_module()
    step_rows = (
        (0, 5),
        (0, 2),
        (1, 7),
        (0, 1),
    )
    flat_inputs = tuple(value for row in step_rows for value in row)

    python_sim = PythonSimulator(module)
    with CppBackendScaffold(namespace="pycmp").build(module, tmp_path) as cpp_sim:
        python_scalar = [python_sim.step_raw(row) for row in step_rows]
        cpp_scalar = [cpp_sim.step_raw(row) for row in step_rows]
        assert python_scalar == cpp_scalar

        python_sim.reset()
        cpp_sim.reset()
        assert python_sim.run_batch_raw(flat_inputs, len(step_rows)) == cpp_sim.run_batch_raw(
            flat_inputs,
            len(step_rows),
        )


def test_python_reference_buffered_and_streaming_paths():
    module = _accum_module()
    python_sim = PythonSimulator(module)
    packed_inputs = pack_u64_words((0, 5, 0, 2, 1, 7, 0, 1))

    assert list(python_sim.run_batch_buffered(packed_inputs, 4)) == [8, 10, 17, 4]
    python_sim.reset()
    chunks = list(python_sim.iter_batch_buffered(((0, 5), (0, 2), (1, 7), (0, 1)), chunk_cycles=3))
    assert [list(chunk) for chunk in chunks] == [[8, 10, 17], [4]]


def test_python_reference_supports_post_state_outputs():
    module = SimModule(
        name="python_post_state",
        signals=(
            Signal("inp", width=8, kind="input"),
            Signal("acc", width=8, kind="state", init=0),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", SignalRef("acc")),
            Assignment("acc", BinaryExpr("+", SignalRef("acc"), SignalRef("inp")), phase="seq"),
        ),
        outputs=("out",),
        outputs_post_state=True,
    )

    python_sim = PythonSimulator(module)
    assert python_sim.step({"inp": 5}) == {"out": 5}
    assert python_sim.step({"inp": 2}) == {"out": 7}


def test_python_reference_supports_latch_phase_state_holding():
    module = SimModule(
        name="python_latch_state",
        signals=(
            Signal("en", width=1, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("state", width=8, kind="state", init=0),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment(
                "state",
                MuxExpr(SignalRef("en"), SignalRef("din"), SignalRef("state")),
                phase="latch",
            ),
            Assignment("out", SignalRef("state")),
        ),
        outputs=("out",),
        outputs_post_state=True,
    )

    python_sim = PythonSimulator(module)
    assert python_sim.step({"en": 0, "din": 0x12}) == {"out": 0x00}
    assert python_sim.step({"en": 1, "din": 0x34}) == {"out": 0x34}
    assert python_sim.step({"en": 0, "din": 0x56}) == {"out": 0x34}


def test_python_reference_supports_comb_read_seq_write_memory():
    module = SimModule(
        name="python_mem",
        signals=(
            Signal("rst", width=1, kind="input"),
            Signal("we", width=1, kind="input"),
            Signal("addr", width=2, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("dout", width=8, kind="output"),
        ),
        assignments=(
            Assignment("dout", MemoryReadExpr("mem", SignalRef("addr"))),
        ),
        outputs=("dout",),
        memories=(Memory("mem", width=8, depth=4, init=(1, 2, 3, 4)),),
        memory_writes=(MemoryWrite("mem", SignalRef("addr"), SignalRef("din"), enable=SignalRef("we")),),
        reset_signal="rst",
        outputs_post_state=True,
    )

    python_sim = PythonSimulator(module)
    assert python_sim.step({"rst": 0, "we": 0, "addr": 0, "din": 0}) == {"dout": 1}
    assert python_sim.step({"rst": 0, "we": 1, "addr": 2, "din": 99}) == {"dout": 99}
    assert python_sim.step({"rst": 0, "we": 0, "addr": 2, "din": 0}) == {"dout": 99}
    assert python_sim.step({"rst": 1, "we": 0, "addr": 2, "din": 0}) == {"dout": 3}


def test_python_reference_honors_reset_branch_value_not_just_init():
    module = SimModule(
        name="python_reset_branch_value",
        signals=(
            Signal("rst", width=1, kind="input"),
            Signal("inp", width=8, kind="input"),
            Signal("state", width=8, kind="state", init=0),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", SignalRef("state")),
            Assignment(
                "state",
                MuxExpr(SignalRef("rst"), ConstExpr(7, 8), SignalRef("inp")),
                phase="seq",
            ),
        ),
        outputs=("out",),
        reset_signal="rst",
        outputs_post_state=True,
    )

    python_sim = PythonSimulator(module)
    assert python_sim.step({"rst": 0, "inp": 9}) == {"out": 9}
    assert python_sim.step({"rst": 1, "inp": 2}) == {"out": 7}
    assert python_sim.step({"rst": 0, "inp": 5}) == {"out": 5}


def test_python_reference_supports_read_first_memory_policy():
    module = SimModule(
        name="python_mem_read_first",
        signals=(
            Signal("we", width=1, kind="input"),
            Signal("addr", width=2, kind="input"),
            Signal("din", width=8, kind="input"),
            Signal("dout", width=8, kind="output"),
        ),
        assignments=(
            Assignment("dout", MemoryReadExpr("mem", SignalRef("addr"))),
        ),
        outputs=("dout",),
        memories=(Memory("mem", width=8, depth=4, init=(1, 2, 3, 4), read_during_write="read_first"),),
        memory_writes=(MemoryWrite("mem", SignalRef("addr"), SignalRef("din"), enable=SignalRef("we")),),
        outputs_post_state=True,
    )

    python_sim = PythonSimulator(module)
    assert python_sim.step({"we": 0, "addr": 2, "din": 0}) == {"dout": 3}
    assert python_sim.step({"we": 1, "addr": 2, "din": 99}) == {"dout": 3}
    assert python_sim.step({"we": 0, "addr": 2, "din": 0}) == {"dout": 99}


def test_python_reference_supports_signed_unsigned_and_arithmetic_shift():
    module = SimModule(
        name="python_signed_ops",
        signals=(
            Signal("inp", width=8, kind="input"),
            Signal("shamt", width=3, kind="input"),
            Signal("signed_out", width=8, kind="output"),
            Signal("unsigned_out", width=8, kind="output"),
            Signal("logical_shift_out", width=8, kind="output"),
            Signal("arith_shift_out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("signed_out", UnaryExpr("$signed", SignalRef("inp"))),
            Assignment("unsigned_out", UnaryExpr("$unsigned", UnaryExpr("~", SignalRef("inp")))),
            Assignment(
                "logical_shift_out",
                MaskExpr(BinaryExpr(">>>", SignalRef("inp"), SignalRef("shamt")), 8),
            ),
            Assignment(
                "arith_shift_out",
                MaskExpr(BinaryExpr(">>>", UnaryExpr("$signed", SignalRef("inp")), SignalRef("shamt")), 8),
            ),
        ),
        outputs=("signed_out", "unsigned_out", "logical_shift_out", "arith_shift_out"),
    )

    python_sim = PythonSimulator(module)
    assert python_sim.step({"inp": 0x80, "shamt": 1}) == {
        "signed_out": 0x80,
        "unsigned_out": 0x7F,
        "logical_shift_out": 0x40,
        "arith_shift_out": 0xC0,
    }


def test_python_reference_wide_logical_shift_zero_fills_unsigned_values():
    module = SimModule(
        name="python_wide_shift",
        signals=(
            Signal("inp", width=80, kind="input"),
            Signal("out", width=80, kind="output"),
        ),
        assignments=(
            Assignment("out", MaskExpr(BinaryExpr(">>", SignalRef("inp"), ConstExpr(4, 3)), 80)),
        ),
        outputs=("out",),
    )

    python_sim = PythonSimulator(module)
    value = (1 << 79) | 0x1234
    assert python_sim.step({"inp": value}) == {"out": value >> 4}


def test_python_reference_wide_buffered_state_round_trip():
    module = SimModule(
        name="python_wide_state",
        signals=(
            Signal("inp", width=128, kind="input"),
            Signal("acc", width=128, kind="state", init=1),
            Signal("out", width=128, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("acc"), SignalRef("inp"))),
            Assignment("acc", SignalRef("out"), phase="seq"),
        ),
        outputs=("out",),
    )

    python_sim = PythonSimulator(module)
    packed_inputs = pack_signal_values_u64_words(
        ((1 << 96) + 5, (1 << 80) + 9),
        (128, 128),
    )

    outputs = python_sim.run_batch_buffered(packed_inputs, 2)
    assert list(outputs) == list(
        pack_signal_values_u64_words(
            ((1 << 96) + 6, (1 << 96) + (1 << 80) + 15),
            (128, 128),
        )
    )
    state_snapshot = python_sim.snapshot_state_values()
    assert state_snapshot == ((1 << 96) + (1 << 80) + 15,)
    packed_state = python_sim.snapshot_state_numpy()
    python_sim.restore_state_numpy(packed_state)
    assert python_sim.snapshot_state_values() == state_snapshot


def test_python_reference_supports_explicit_multi_clock_domains():
    module = _dual_clock_fifo_like_module()
    python_sim = PythonSimulator(module)

    with pytest.raises(ValueError, match="step_clocks"):
        python_sim.step({"wr_en": 0, "rd_en": 0, "din": 0})

    assert python_sim.step_clocks({"wr_en": 1, "din": 11}, ("wr_clk",)) == {"dout": 0}
    assert python_sim.step_clocks({"wr_en": 1, "din": 22}, ("wr_clk",)) == {"dout": 0}
    assert python_sim.step_clocks({"rd_en": 1}, ("rd_clk",)) == {"dout": 11}
    assert python_sim.step_clocks({"rd_en": 1}, ("rd_clk",)) == {"dout": 22}
    assert python_sim.step_clocks({"rd_rst": 1}, ("rd_clk",)) == {"dout": 0}


def test_python_reference_prefers_named_multi_clock_domains_but_accepts_signal_aliases():
    python_sim = PythonSimulator(_named_dual_clock_fifo_like_module())

    assert python_sim.step_clocks({"wr_en": 1, "din": 11}, ("write",)) == {"dout": 0}
    assert python_sim.step_clocks({"wr_en": 1, "din": 22}, ("wr_clk",)) == {"dout": 0}
    assert python_sim.step_clocks({"rd_en": 1}, ("read",)) == {"dout": 11}
    assert python_sim.step_clocks({"rd_en": 1}, ("rd_clk",)) == {"dout": 22}
    assert python_sim.step_clocks({"rd_rst": 1}, ("read",)) == {"dout": 0}


def test_python_reference_multi_clock_batch_paths_fail_fast():
    python_sim = PythonSimulator(_dual_clock_fifo_like_module())

    with pytest.raises(ValueError, match="single-clock"):
        python_sim.run_batch_raw((0, 0, 0, 0, 0, 0, 0), 1)
    with pytest.raises(ValueError, match="single-clock"):
        python_sim.run_batch(((0, 0, 0, 0, 0, 0, 0),))


def test_reset_simulator_adapter_handles_new_runtime_no_args():
    """Finding #6: reset_simulator() must reset the new PythonSimulator (no-arg
    reset) and ignore rst/cycles arguments it does not understand."""
    from rtlgen_x.sim import reset_simulator

    module = _accum_module()
    sim = PythonSimulator(module)
    # Step a few times to dirty the accumulator state.
    sim.step({"rst": 0, "inp": 5})
    sim.step({"rst": 0, "inp": 5})
    assert sim.snapshot_state_values() != (3,)

    # rst/cycles are accepted but ignored for the new runtime.
    reset_simulator(sim, rst="rst", cycles=2)
    assert sim.snapshot_state_values() == (3,)


def test_reset_simulator_adapter_forwards_older_rst_cycles():
    """Finding #6: reset_simulator() must forward rst/cycles to a older-style
    simulator whose reset() accepts those parameters."""
    from rtlgen_x.sim import reset_simulator

    class CompatFakeSim:
        """Minimal stand-in for the older Simulator reset() signature."""

        def __init__(self):
            self.last_kwargs = {}

        def reset(self, rst=None, cycles=2):
            self.last_kwargs = {"rst": rst, "cycles": cycles}

    compat = CompatFakeSim()
    reset_simulator(compat, rst="rst_n", cycles=4)
    assert compat.last_kwargs == {"rst": "rst_n", "cycles": 4}

    # Calling with no overrides still works and uses the older defaults.
    reset_simulator(compat)
    assert compat.last_kwargs == {"rst": None, "cycles": 2}
