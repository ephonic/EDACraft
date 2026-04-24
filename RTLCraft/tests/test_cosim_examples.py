import pytest

from rtlgen.cosim import CosimRunner


def test_full_adder():
    from full_adder import FullAdder

    vectors = [{"a": a, "b": b, "cin": c} for a in (0, 1) for b in (0, 1) for c in (0, 1)]
    CosimRunner(FullAdder(), vectors, mode="comb").run(verbose=True)


def test_half_adder():
    from submodule_inst_demo import HalfAdder

    vectors = [{"a": a, "b": b} for a in (0, 1) for b in (0, 1)]
    CosimRunner(HalfAdder(), vectors, mode="comb").run(verbose=True)


def test_ripple_adder():
    from generate_for_inst_demo import RippleAdder

    vectors = [
        {"a": 0b0000, "b": 0b0000, "cin": 0},
        {"a": 0b0001, "b": 0b0010, "cin": 0},
        {"a": 0b1111, "b": 0b0001, "cin": 0},
        {"a": 0b1111, "b": 0b1111, "cin": 1},
    ]
    CosimRunner(RippleAdder(width=4), vectors, mode="comb").run(verbose=True)


def test_counter():
    from counter import Counter

    vectors = [
        {"en": 0},
        {"en": 1},
        {"en": 1},
        {"en": 1},
        {"en": 0},
        {"en": 1},
    ]
    CosimRunner(Counter(width=4), vectors, mode="seq").run(verbose=True)


def test_decoder():
    from rtlgen import Decoder

    vectors = [{"sel": s} for s in range(4)]
    CosimRunner(Decoder(in_width=2), vectors, mode="comb").run(verbose=True)


def test_genif_and():
    from genif_demo import CondGen

    vectors = [{"a": 0b1010, "b": 0b1100}, {"a": 0b1111, "b": 0b0000}]
    CosimRunner(CondGen(), vectors, mode="comb").run(verbose=True)


def test_genif_or():
    from genif_demo import CondGen

    vectors = [{"a": 0b1010, "b": 0b1100}, {"a": 0b1111, "b": 0b0000}]
    cg = CondGen()
    cg.USE_AND.value = 0
    CosimRunner(cg, vectors, mode="comb").run(verbose=True)


def test_param_auto():
    from param_auto_demo import ParamAdder, Top

    vectors = [{"a": 10, "b": 20}, {"a": 255, "b": 1}]
    CosimRunner(ParamAdder(name="ParamAdder8"), vectors, mode="comb").run(verbose=True)

    vectors = [{"a": 1000, "b": 2000}, {"a": 65535, "b": 1}]
    CosimRunner(Top(), vectors, mode="comb").run(verbose=True)


def test_simple_ram():
    from sim_memory_demo import SimpleRAM

    vectors = [
        {"addr": 0, "din": 0xAB, "we": 1},
        {"addr": 1, "din": 0xCD, "we": 1},
        {"addr": 2, "din": 0xEF, "we": 1},
        {"addr": 0, "din": 0, "we": 0},
        {"addr": 1, "din": 0, "we": 0},
        {"addr": 2, "din": 0, "we": 0},
    ]
    CosimRunner(SimpleRAM(width=8, depth=16), vectors, mode="seq").run(verbose=True)
