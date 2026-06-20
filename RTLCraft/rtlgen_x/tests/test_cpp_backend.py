import pytest
import random

from rtlgen_x.sim import (
    Assignment,
    BinaryExpr,
    compare_python_and_compiled,
    ConstExpr,
    CppBuildError,
    CppBackendScaffold,
    MaskExpr,
    Memory,
    MemoryReadExpr,
    MemoryWrite,
    MuxExpr,
    pack_u64_numpy,
    pack_u64_numpy_rows,
    pack_u64_words,
    Signal,
    SignalRef,
    SimModule,
    UnaryExpr,
)


def test_sim_module_rejects_duplicate_signal_names():
    with pytest.raises(ValueError, match="duplicate signal"):
        SimModule(
            name="dup",
            signals=(
                Signal("a", width=8, kind="input"),
                Signal("a", width=8, kind="output"),
            ),
            assignments=(),
            outputs=("a",),
        )


def test_sim_module_rejects_seq_assignment_to_non_state_target():
    with pytest.raises(ValueError, match="sequential assignments"):
        SimModule(
            name="bad_seq",
            signals=(
                Signal("inp", width=8, kind="input"),
                Signal("out", width=8, kind="output"),
            ),
            assignments=(
                Assignment("out", SignalRef("inp"), phase="seq"),
            ),
            outputs=("out",),
        )


def test_cpp_backend_scaffold_emits_reset_and_step_structure():
    module = SimModule(
        name="accum",
        signals=(
            Signal("rst", width=1, kind="input"),
            Signal("inp", width=8, kind="input"),
            Signal("sel", width=1, kind="input"),
            Signal("acc", width=8, kind="state", init=3),
            Signal("sum_out", width=8, kind="wire"),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("sum_out", BinaryExpr("+", SignalRef("acc"), SignalRef("inp"))),
            Assignment("out", MuxExpr(SignalRef("sel"), SignalRef("sum_out"), ConstExpr(0, 8))),
            Assignment("acc", SignalRef("sum_out"), phase="seq"),
        ),
        outputs=("out",),
        reset_signal="rst",
    )

    source = CppBackendScaffold(namespace="testsim").emit_translation_unit(module)

    assert "namespace testsim" in source
    assert "struct accumState" in source
    assert "struct accumInputs" in source
    assert "struct accumOutputs" in source
    assert "state_ = initial_state();" in source
    assert "if (in.rst)" in source
    assert "next_state.acc" in source
    assert "outputs.out = value_out;" in source


def test_compiled_simulator_builds_and_executes_stateful_module(tmp_path):
    module = SimModule(
        name="accum_runtime",
        signals=(
            Signal("inp", width=8, kind="input"),
            Signal("acc", width=8, kind="state", init=3),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("acc"), SignalRef("inp"))),
            Assignment("acc", SignalRef("out"), phase="seq"),
        ),
        outputs=("out",),
    )

    with CppBackendScaffold(namespace="testrun").build(module, tmp_path) as sim:
        assert sim.source_path.exists()
        assert sim.library_path.exists()
        assert sim.step({"inp": 5}) == {"out": 8}
        assert sim.step({"inp": 2}) == {"out": 10}
        sim.reset()
        assert sim.step({}) == {"out": 3}
        with pytest.raises(KeyError, match="unknown simulator inputs"):
            sim.step({"bad": 1})


def test_compiled_simulator_honors_reset_input(tmp_path):
    module = SimModule(
        name="accum_with_reset",
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

    with CppBackendScaffold(namespace="testrst").build(module, tmp_path) as sim:
        assert sim.step({"rst": 0, "inp": 5}) == {"out": 8}
        assert sim.step({"rst": 1, "inp": 2}) == {"out": 10}
        assert sim.step({"rst": 0, "inp": 1}) == {"out": 4}


def test_compiled_simulator_buffered_and_streaming_batch(tmp_path):
    module = SimModule(
        name="accum_batch",
        signals=(
            Signal("inp", width=8, kind="input"),
            Signal("acc", width=8, kind="state", init=3),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("acc"), SignalRef("inp"))),
            Assignment("acc", SignalRef("out"), phase="seq"),
        ),
        outputs=("out",),
    )
    packed_inputs = pack_u64_words((5, 2, 1))

    with CppBackendScaffold(namespace="testbatch").build(module, tmp_path) as sim:
        assert list(sim.run_batch_buffered(packed_inputs, 3)) == [8, 10, 11]
        sim.reset()
        assert list(sim.run_batch_buffered(pack_u64_numpy((5, 2, 1)), 3)) == [8, 10, 11]
        sim.reset()
        assert sim.run_batch_matrix(pack_u64_numpy_rows(((5,), (2,), (1,)))).tolist() == [[8], [10], [11]]
        snapshot = sim.snapshot_state_numpy()
        sim.step({"inp": 4})
        sim.restore_state_numpy(snapshot)
        assert sim.step({"inp": 4}) == {"out": 15}
        sim.reset()
        chunks = list(sim.iter_batch_buffered(((5,), (2,), (1,)), chunk_cycles=2))
        assert [list(chunk) for chunk in chunks] == [[8, 10], [11]]


def test_compiled_simulator_can_recompute_outputs_after_state_commit(tmp_path):
    module = SimModule(
        name="accum_post_state",
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

    with CppBackendScaffold(namespace="testpost").build(module, tmp_path) as sim:
        assert sim.step({"inp": 5}) == {"out": 5}
        assert sim.step({"inp": 2}) == {"out": 7}


def test_compiled_backend_supports_wide_signal_modules(tmp_path):
    module = SimModule(
        name="wide_runtime",
        signals=(
            Signal("inp", width=128, kind="input"),
            Signal("acc", width=128, kind="state", init=1),
            Signal("out", width=128, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("+", SignalRef("inp"), SignalRef("acc"))),
            Assignment("acc", SignalRef("out"), phase="seq"),
        ),
        outputs=("out",),
    )

    with CppBackendScaffold(namespace="wideguard").build(module, tmp_path) as sim:
        assert sim.step({"inp": (1 << 96) + 5}) == {"out": (1 << 96) + 6}
        assert sim.step({"inp": (1 << 80) + 9}) == {"out": (1 << 96) + (1 << 80) + 15}
        snapshot = sim.snapshot_state_values()
        assert snapshot == ((1 << 96) + (1 << 80) + 15,)
        sim.restore_state_values((3,))
        assert sim.step({"inp": 7}) == {"out": 10}


def test_compiled_simulator_supports_comb_read_seq_write_memory(tmp_path):
    module = SimModule(
        name="mem_runtime",
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
        memories=(
            Memory("mem", width=8, depth=4, init=(1, 2, 3, 4)),
        ),
        memory_writes=(
            MemoryWrite("mem", SignalRef("addr"), SignalRef("din"), enable=SignalRef("we")),
        ),
        reset_signal="rst",
        outputs_post_state=True,
    )

    with CppBackendScaffold(namespace="testmem").build(module, tmp_path) as sim:
        assert sim.step({"rst": 0, "we": 0, "addr": 0, "din": 0}) == {"dout": 1}
        assert sim.step({"rst": 0, "we": 1, "addr": 2, "din": 99}) == {"dout": 99}
        snapshot = sim.snapshot_state_numpy()
        assert sim.state_names == ("mem[0]", "mem[1]", "mem[2]", "mem[3]")
        assert snapshot.tolist() == [1, 2, 99, 4]
        assert sim.step({"rst": 0, "we": 0, "addr": 2, "din": 0}) == {"dout": 99}
        assert sim.step({"rst": 1, "we": 0, "addr": 2, "din": 0}) == {"dout": 3}


def test_compiled_simulator_supports_signed_unsigned_and_arithmetic_shift(tmp_path):
    module = SimModule(
        name="cpp_signed_ops",
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

    with CppBackendScaffold(namespace="testsigned").build(module, tmp_path) as sim:
        assert sim.step({"inp": 0x80, "shamt": 1}) == {
            "signed_out": 0x80,
            "unsigned_out": 0x7F,
            "logical_shift_out": 0x40,
            "arith_shift_out": 0xC0,
        }


def test_compiled_simulator_randomized_python_parity(tmp_path):
    module = SimModule(
        name="cpp_random_parity",
        signals=(
            Signal("a", width=8, kind="input"),
            Signal("b", width=8, kind="input"),
            Signal("acc", width=8, kind="state", init=7),
            Signal("out", width=8, kind="output"),
        ),
        assignments=(
            Assignment("out", BinaryExpr("^", BinaryExpr("+", SignalRef("acc"), SignalRef("a")), SignalRef("b"))),
            Assignment("acc", BinaryExpr("+", SignalRef("acc"), SignalRef("a")), phase="seq"),
        ),
        outputs=("out",),
    )
    rng = random.Random(1234)
    vectors = tuple({"a": rng.randrange(256), "b": rng.randrange(256)} for _ in range(64))

    report = compare_python_and_compiled(
        module,
        vectors,
        builder=CppBackendScaffold(),
        build_dir=tmp_path / "random_parity",
    )

    assert report.matched is True
    assert report.mismatches == ()
