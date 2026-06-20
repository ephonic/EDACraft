from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
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
