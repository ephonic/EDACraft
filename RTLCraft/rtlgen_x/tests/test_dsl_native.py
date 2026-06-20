from rtlgen_x.dsl import NativeModuleBuilder, const, mux
from rtlgen_x.sim import PythonSimulator


def test_native_dsl_builds_executable_module():
    builder = NativeModuleBuilder("native_accum")
    inp = builder.input("inp", width=8)
    sel = builder.input("sel", width=1)
    acc = builder.state("acc", width=8, init=3)
    tmp = builder.wire("tmp", width=9)
    out = builder.output("out", width=8)

    builder.comb(tmp, acc + inp)
    builder.comb(out, mux(sel, tmp.mask(8), const(0, width=8)))
    builder.seq(acc, tmp.mask(8))
    module = builder.build()

    sim = PythonSimulator(module)
    assert sim.step({"inp": 5, "sel": 1}) == {"out": 8}
    assert sim.step({"inp": 2, "sel": 1}) == {"out": 10}
    sim.reset()
    assert sim.step({"inp": 1, "sel": 0}) == {"out": 0}


def test_native_dsl_supports_memory_read_write():
    builder = NativeModuleBuilder("native_mem")
    we = builder.input("we", width=1)
    addr = builder.input("addr", width=2)
    din = builder.input("din", width=8)
    dout = builder.output("dout", width=8)
    mem = builder.memory("mem", width=8, depth=4, init=(1, 2, 3, 4))

    builder.comb(dout, mem[addr])
    builder.write_memory(mem, addr=addr, value=din, enable=we)
    module = builder.build(outputs_post_state=True)

    sim = PythonSimulator(module)
    assert sim.step({"we": 0, "addr": 0, "din": 0}) == {"dout": 1}
    assert sim.step({"we": 1, "addr": 2, "din": 99}) == {"dout": 99}
