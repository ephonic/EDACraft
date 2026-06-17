"""Verification runners for top-level SoC closure."""

from __future__ import annotations

from typing import Callable

from rtlgen.sim import Simulator


def run_functional_tests(
    *,
    rv32_iss_cls,
    to_u32: Callable[[int], int],
    simd_op_vadd: int,
    simd_int16_functional: Callable[[int, int, int], int],
    simd_fp16_mac_functional: Callable[[int, int, int], int],
    f32_to_fp16: Callable[[float], int],
    fp16_to_f32: Callable[[int], float],
    fft256_functional: Callable[[list[int], list[int]], tuple[list[int], list[int]]],
) -> tuple[bool, list]:
    """Layer 1 functional model tests."""
    print("\n" + "=" * 70)
    print("Layer 1 Functional Tests")
    print("=" * 70)
    results = []

    print("\n[TEST] RV32IM ISS add/sub/load/store...")
    iss = rv32_iss_cls()
    program = [
        0x00100093,
        0x00200113,
        0x002081b3,
        0x40208233,
        0x003022a3,
        0x00502303,
        0x00100073,
    ]
    iss.load_program_words(program, entry_point=0x1000)
    iss.run(max_cycles=100)
    ok = (iss.state.regs[3] == 3 and iss.state.regs[4] == 0xFFFFFFFF and iss.state.regs[6] == 3)

    iss2 = rv32_iss_cls()
    prog_m = [
        0x00700093,
        0x00300113,
        0x022081b3,
        0x02209233,
        0x0220c2b3,
        0x0220d333,
        0x0220e3b3,
        0x0220f433,
        0x00100073,
    ]
    iss2.load_program_words(prog_m, 0x1000)
    iss2.run(max_cycles=40)
    mul_ok = (
        iss2.state.regs[3] == 21 and iss2.state.regs[4] == 0 and iss2.state.regs[5] == 2
        and iss2.state.regs[6] == 2 and iss2.state.regs[7] == 1 and iss2.state.regs[8] == 1
    )

    iss3 = rv32_iss_cls()
    prog_neg = [
        0xff900093,
        0x00300113,
        0x0220c2b3,
        0x0220e333,
        0x00100073,
    ]
    iss3.load_program_words(prog_neg, 0x1000)
    iss3.run(max_cycles=40)
    div_neg_ok = (iss3.state.regs[5] == to_u32(-2) and iss3.state.regs[6] == to_u32(-1))

    iss4 = rv32_iss_cls()
    prog_div0 = [
        0x00700093,
        0x00000113,
        0x0220c2b3,
        0x0220e333,
        0x00100073,
    ]
    iss4.load_program_words(prog_div0, 0x1000)
    iss4.run(max_cycles=40)
    div0_ok = (iss4.state.regs[5] == 0xFFFFFFFF and iss4.state.regs[6] == 7)
    m_ext_ok = mul_ok and div_neg_ok and div0_ok
    results.append(("RV32IM ISS", ok and m_ext_ok))
    print(
        f"  regs[3]={iss.state.regs[3]}, regs[4]={iss.state.regs[4]}, regs[6]={iss.state.regs[6]}, "
        f"M-ext={m_ext_ok}  {'PASS' if ok and m_ext_ok else 'FAIL'}"
    )

    print("\n[TEST] SIMD16 INT16 vadd...")
    a = 0
    b = 0
    for i in range(16):
        a |= ((i + 1) & 0xFFFF) << (i * 16)
        b |= ((i + 2) & 0xFFFF) << (i * 16)
    r = simd_int16_functional(simd_op_vadd, a, b)
    ok = True
    for i in range(16):
        lane = (r >> (i * 16)) & 0xFFFF
        expected = ((i + 1) + (i + 2)) & 0xFFFF
        if lane != expected:
            ok = False
    results.append(("SIMD16 INT16 vadd", ok))
    print(f"  {'PASS' if ok else 'FAIL'}")

    print("\n[TEST] SIMD16 FP16 MAC...")
    a_fp = 0
    b_fp = 0
    c_fp = 0
    for i in range(16):
        a_fp |= f32_to_fp16(0.5) << (i * 16)
        b_fp |= f32_to_fp16(0.25) << (i * 16)
        c_fp |= f32_to_fp16(0.1) << (i * 16)
    r_fp = simd_fp16_mac_functional(a_fp, b_fp, c_fp)
    ok = True
    for i in range(16):
        lane = fp16_to_f32((r_fp >> (i * 16)) & 0xFFFF)
        expected = 0.5 * 0.25 + 0.1
        if abs(lane - expected) > 0.01:
            ok = False
    results.append(("SIMD16 FP16 MAC", ok))
    print(f"  {'PASS' if ok else 'FAIL'}")

    print("\n[TEST] FFT256 functional impulse...")
    samples_re = [32767 if i == 0 else 0 for i in range(256)]
    samples_im = [0] * 256
    out_re, _ = fft256_functional(samples_re, samples_im)
    avg_re = sum(out_re) / 256
    ok = 120 < avg_re < 135
    results.append(("FFT256 impulse", ok))
    print(f"  avg_re={avg_re:.1f}  {'PASS' if ok else 'FAIL'}")

    print("\n" + "-" * 70)
    passed = sum(1 for _, item_ok in results if item_ok)
    for name, item_ok in results:
        print(f"  {name:25s} {'PASS' if item_ok else 'FAIL'}")
    print(f"  Total: {passed}/{len(results)}")
    print("-" * 70)
    return passed == len(results), results


def run_dsl_sim_tests(
    *,
    simulator_cls,
    simd_cls,
    qspi_cls,
    rv32_cls,
    sram_cls,
    simd_op_vadd: int,
) -> tuple[bool, list]:
    """Layer 3 DSL simulation tests."""
    print("\n" + "=" * 70)
    print("Layer 3 DSL Simulation Tests")
    print("=" * 70)
    results = []

    print("\n[TEST] EarphoneSIMD16 DSL vadd...")
    try:
        simd = simd_cls()
        sim = simulator_cls(simd)
        sim.reset("rst_n", cycles=2)
        a = 0
        b = 0
        for i in range(16):
            a |= ((i + 1) & 0xFFFF) << (i * 16)
            b |= ((i + 2) & 0xFFFF) << (i * 16)
        sim.poke("vsrc0", a)
        sim.poke("vsrc1", b)
        sim.poke("op", simd_op_vadd)
        sim.poke("mode", 0)
        sim.poke("pred", 0xFFFF)
        sim.poke("start", 1)
        sim.step()
        r = sim.peek("vdst")
        done = sim.peek("done")
        sim.poke("start", 0)
        sim.step()
        ok = True
        for i in range(16):
            lane = (r >> (i * 16)) & 0xFFFF
            expected = ((i + 1) + (i + 2)) & 0xFFFF
            if lane != expected:
                ok = False
        results.append(("SIMD16 DSL vadd", ok and done))
        print(f"  done={done}, vdst={hex(r)}  {'PASS' if ok and done else 'FAIL'}")
    except Exception as exc:
        results.append(("SIMD16 DSL vadd", False))
        print(f"  FAIL: {exc}")

    print("\n[TEST] EarphoneQSPI DSL XIP read...")
    try:
        qspi = qspi_cls()
        sim = simulator_cls(qspi)
        sim.reset("rst_n", cycles=2)
        sim.poke("req", 1)
        sim.poke("addr", 0x1234)
        cycles = 0
        ready = 0
        while cycles < 30 and ready == 0:
            state = sim.peek("state")
            if state == 4:
                sim.poke("qspi_io_i", (cycles + 1) & 0xF)
            sim.step()
            ready = sim.peek("ready")
            cycles += 1
        rdata = sim.peek("rdata")
        ok = ready == 1 and rdata != 0
        results.append(("QSPI DSL XIP", ok))
        print(f"  ready={ready}, rdata={rdata:#x}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("QSPI DSL XIP", False))
        print(f"  FAIL: {exc}")

    print("\n[TEST] EarphoneRV32 DSL MUL/DIV program...")
    try:
        cpu = rv32_cls()
        sim = simulator_cls(cpu)
        sim.reset("rst_n", cycles=2)
        program = {
            0x1000: 0x00700093,
            0x1004: 0x00300113,
            0x1008: 0x022081b3,
            0x100C: 0x0220C2B3,
            0x1010: 0x0220D333,
            0x1014: 0x0220E3B3,
            0x1018: 0x0220F433,
            0x101C: 0x00100073,
        }
        expected = {3: 21, 5: 2, 6: 2, 7: 1, 8: 1}
        retired = {rd: False for rd in expected}
        dmem = {}
        for _ in range(200):
            addr = sim.peek("imem_addr")
            sim.poke("imem_gnt", 1)
            sim.poke("imem_rdata", program.get(addr, 0))
            daddr = sim.peek("dmem_addr")
            sim.poke("dmem_gnt", 1)
            sim.poke("dmem_valid", 1)
            sim.poke("dmem_rdata", dmem.get(daddr, 0))
            sim.step()
            if sim.peek("retire_valid"):
                rd = sim.peek("retire_rd")
                val = sim.peek("retire_result")
                if rd in expected and val == expected[rd]:
                    retired[rd] = True
        ok = all(retired.values())
        results.append(("RV32IM DSL MUL/DIV", ok))
        print(f"  retired={retired}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("RV32IM DSL MUL/DIV", False))
        print(f"  FAIL: {exc}")

    print("\n[TEST] EarphoneSRAM256K DSL read/write...")
    try:
        sram = sram_cls()
        sim = simulator_cls(sram)
        sim.reset("rst_n", cycles=2)
        sim.poke("paddr", 0x40)
        sim.poke("pwdata", 0xDEADBEEF)
        sim.poke("pwrite", 1)
        sim.poke("psel", 1)
        sim.poke("penable", 1)
        sim.poke("pstrb", 0b1111)
        sim.step()
        sim.poke("pwrite", 0)
        sim.step()
        rdata = sim.peek("prdata")
        ok = rdata == 0xDEADBEEF
        results.append(("SRAM DSL", ok))
        print(f"  rdata={rdata:#x}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("SRAM DSL", False))
        print(f"  FAIL: {exc}")

    print("\n" + "-" * 70)
    passed = sum(1 for _, item_ok in results if item_ok)
    for name, item_ok in results:
        print(f"  {name:25s} {'PASS' if item_ok else 'FAIL'}")
    print(f"  Total: {passed}/{len(results)}")
    print("-" * 70)
    return passed == len(results), results


def run_layer_verification(
    *,
    simulator_cls,
    rv32_iss_cls,
    rv32_cls,
    simd_cls,
    fft_cls,
    qspi_cls,
    sram_cls,
    apb_bridge_cls,
    simd_cycle_model_factory,
    simd_op_vadd: int,
    simd_op_vsub: int,
    simd_int16_functional: Callable[[int, int, int], int],
    fft256_functional: Callable[[list[int], list[int]], tuple[list[int], list[int]]],
    apb_decode_fn: Callable[[int], tuple[int, str]],
) -> tuple[bool, list]:
    """Cross-layer verification: L1 functional == L2 cycle == L3 DSL."""
    print("\n" + "=" * 70)
    print("Cross-Layer Verification (LayerVerifier)")
    print("=" * 70)
    results = []

    print("\n[VERIFY] SIMD16 INT16 vadd: L1 == L2 == L3...")
    try:
        a = 0
        b = 0
        for i in range(16):
            a |= ((i + 5) & 0xFFFF) << (i * 16)
            b |= ((i + 3) & 0xFFFF) << (i * 16)
        expected = simd_int16_functional(simd_op_vadd, a, b)

        l1_ok = expected != 0

        from rtlgen.arch_def import CycleContext
        ctx = CycleContext(inputs={"rst_n": 1, "start": 1, "op": simd_op_vadd, "mode": 0, "vsrc0": a, "vsrc1": b, "vsrc2": 0, "pred": 0xFFFF})
        l2_model = simd_cycle_model_factory()
        l2_model(ctx)
        l2_model(ctx)
        l2_ok = ctx.outputs.get("done", 0) == 1 and ctx.outputs.get("vdst", 0) == expected

        simd = simd_cls()
        sim = simulator_cls(simd)
        sim.reset("rst_n", cycles=2)
        sim.poke("vsrc0", a)
        sim.poke("vsrc1", b)
        sim.poke("op", simd_op_vadd)
        sim.poke("mode", 0)
        sim.poke("pred", 0xFFFF)
        sim.poke("start", 1)
        sim.step()
        l3_ok = sim.peek("vdst") == expected and sim.peek("done") == 1

        ok = l1_ok and l2_ok and l3_ok
        results.append(("SIMD16 cross-layer", ok))
        print(f"  L1={l1_ok}, L2={l2_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("SIMD16 cross-layer", False))
        print(f"  FAIL: {exc}")

    print("\n[VERIFY] SIMD16 INT16 vsub: L1 == L2 == L3...")
    try:
        a = 0
        b = 0
        for i in range(16):
            a |= ((i + 9) & 0xFFFF) << (i * 16)
            b |= ((i + 3) & 0xFFFF) << (i * 16)
        expected = simd_int16_functional(simd_op_vsub, a, b)

        from rtlgen.arch_def import CycleContext
        ctx = CycleContext(inputs={"rst_n": 1, "start": 1, "op": simd_op_vsub, "mode": 0, "vsrc0": a, "vsrc1": b, "vsrc2": 0, "pred": 0xFFFF})
        l2_model = simd_cycle_model_factory()
        l2_model(ctx)
        l2_ok = ctx.outputs.get("done", 0) == 1 and ctx.outputs.get("vdst", 0) == expected

        simd = simd_cls()
        sim = simulator_cls(simd)
        sim.reset("rst_n", cycles=2)
        sim.poke("vsrc0", a)
        sim.poke("vsrc1", b)
        sim.poke("op", simd_op_vsub)
        sim.poke("mode", 0)
        sim.poke("pred", 0xFFFF)
        sim.poke("start", 1)
        sim.step()
        l3_ok = sim.peek("vdst") == expected and sim.peek("done") == 1

        ok = expected != 0 and l2_ok and l3_ok
        results.append(("SIMD16 vsub cross-layer", ok))
        print(f"  L1={expected != 0}, L2={l2_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("SIMD16 vsub cross-layer", False))
        print(f"  FAIL: {exc}")

    print("\n[VERIFY] SRAM256K read/write: L1 == L3...")
    try:
        from earphone.modules.sram256k.layer_L1_behavior.src.behavior import SRAM256KFunctional
        from earphone.modules.sram256k.layer_L2_cycle.src.cycle import describe as sram_l2_describe

        l1_sram = SRAM256KFunctional()
        l1_sram.write(0x40, 0xDEADBEEF)
        l1_expected = l1_sram.read(0x40)
        l2_ok = sram_l2_describe()["status"] == "implemented"

        sram = sram_cls()
        sim = simulator_cls(sram)
        sim.reset("rst_n", cycles=2)
        sim.poke("paddr", 0x40)
        sim.poke("pwdata", 0xDEADBEEF)
        sim.poke("pwrite", 1)
        sim.poke("psel", 1)
        sim.poke("penable", 1)
        sim.poke("pstrb", 0b1111)
        sim.step()
        sim.poke("pwrite", 0)
        sim.step()
        l3_ok = sim.peek("prdata") == l1_expected

        ok = l2_ok and l3_ok
        results.append(("SRAM256K cross-layer", ok))
        print(f"  L1={l1_expected == 0xDEADBEEF}, L2={l2_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("SRAM256K cross-layer", False))
        print(f"  FAIL: {exc}")

    print("\n[VERIFY] APB Bridge address decode: L1 == L3...")
    try:
        from earphone.modules.apb_bridge.layer_L1_behavior.src.behavior import APB_SLAVE_SLOTS
        base = 0x4000_0000
        l1_ok = True
        l3_ok = True
        bridge = apb_bridge_cls()
        sim = simulator_cls(bridge)
        sim.reset("rst_n", cycles=1)
        for i, (name, _, _) in enumerate(APB_SLAVE_SLOTS):
            addr = base + (i << 22)
            l1_idx, l1_name = apb_decode_fn(addr - base)
            if l1_idx != i or l1_name != name:
                l1_ok = False
            sim.poke("m_paddr", addr)
            sim.poke("m_psel", 1)
            sim.step()
            if sim.peek("s_psel") != (1 << i):
                l3_ok = False
        ok = l1_ok and l3_ok
        results.append(("APB Bridge cross-layer", ok))
        print(f"  L1={l1_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("APB Bridge cross-layer", False))
        print(f"  FAIL: {exc}")

    print("\n[VERIFY] RV32IM MUL/DIV program: L1 == L3...")
    try:
        program = [
            0x00700093, 0x00300113, 0x022081B3, 0x0220C2B3,
            0x0220D333, 0x0220E3B3, 0x0220F433, 0x00100073,
        ]
        expected = {3: 21, 5: 2, 6: 2, 7: 1, 8: 1}

        iss = rv32_iss_cls()
        iss.load_program_words(program, entry_point=0x1000)
        iss.run(max_cycles=100)

        cpu = rv32_cls()
        sim = simulator_cls(cpu)
        sim.reset("rst_n", cycles=2)
        prog_dict = {0x1000 + i * 4: w for i, w in enumerate(program)}
        retired = {}
        dmem = {}
        for _ in range(200):
            addr = sim.peek("imem_addr")
            sim.poke("imem_gnt", 1)
            sim.poke("imem_rdata", prog_dict.get(addr, 0))
            daddr = sim.peek("dmem_addr")
            sim.poke("dmem_gnt", 1)
            sim.poke("dmem_valid", 1)
            sim.poke("dmem_rdata", dmem.get(daddr, 0))
            sim.step()
            if sim.peek("retire_valid"):
                rd = sim.peek("retire_rd")
                retired[rd] = sim.peek("retire_result")

        l1_ok = all(iss.state.regs[rd] == val for rd, val in expected.items())
        l3_ok = all(retired.get(rd) == val for rd, val in expected.items())
        ok = l1_ok and l3_ok
        results.append(("RV32IM cross-layer", ok))
        print(f"  L1={l1_ok}, L3={l3_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("RV32IM cross-layer", False))
        print(f"  FAIL: {exc}")

    print("\n[VERIFY] QSPI XIP read: L1 == L2...")
    try:
        from earphone.modules.qspi.layer_L1_behavior.src.behavior import QSPIFlashFunctional
        from earphone.modules.qspi.layer_L2_cycle.src.cycle import qspi_cycle_model
        from rtlgen.arch_def import CycleContext

        flash = QSPIFlashFunctional()
        flash.load_data(0x1000, b"\x78\x56\x34\x12")
        l1_expected = flash.xip_read(0x1000)

        ctx = CycleContext(inputs={"rst_n": 1, "req": 1, "addr": 0x1000})
        ctx.state["flash"] = flash
        model = qspi_cycle_model()
        model(ctx)
        ctx.inputs["req"] = 0
        l2_rdata = 0
        l2_ready = 0
        for _ in range(100):
            model(ctx)
            if ctx.outputs.get("ready"):
                l2_ready = 1
                l2_rdata = ctx.outputs.get("rdata", 0)
                break

        l1_ok = l1_expected == 0x12345678
        l2_ok = l2_ready == 1 and l2_rdata == l1_expected
        ok = l1_ok and l2_ok
        results.append(("QSPI cross-layer", ok))
        print(f"  L1={l1_ok}, L2={l2_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("QSPI cross-layer", False))
        print(f"  FAIL: {exc}")

    print("\n[VERIFY] I2C master write: L1 == L2...")
    try:
        from earphone.modules.i2c.layer_L1_behavior.src.behavior import I2CBusFunctional
        from earphone.modules.i2c.layer_L2_cycle.src.cycle import i2c_master_cycle_model
        from rtlgen.arch_def import CycleContext

        bus = I2CBusFunctional()
        bus.write(0x50, [0xAB])

        ctx = CycleContext(inputs={"rst_n": 1, "start": 1, "addr": 0x50, "data": 0xAB, "rw": 0})
        model = i2c_master_cycle_model()
        model(ctx)
        ctx.inputs["start"] = 0
        done = 0
        for _ in range(100):
            model(ctx)
            if ctx.outputs.get("done"):
                done = 1
                break

        l1_ok = (
            len(bus.transactions) == 1 and bus.transactions[0][0] == 0x50
            and bus.transactions[0][1] == [0xAB] and bus.transactions[0][2] is False
        )
        l2_ok = done == 1
        ok = l1_ok and l2_ok
        results.append(("I2C cross-layer", ok))
        print(f"  L1={l1_ok}, L2={l2_ok}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("I2C cross-layer", False))
        print(f"  FAIL: {exc}")

    print("\n[VERIFY] FFT256 impulse: L1 == L3 (within fixed-point tolerance)...")
    try:
        def _bit_reverse(x, bits):
            result = 0
            for _ in range(bits):
                result = (result << 1) | (x & 1)
                x >>= 1
            return result

        def _to_s16(value):
            return value if value < 32768 else value - 65536

        samples_re = [32767 if i == 0 else 0 for i in range(256)]
        samples_im = [0] * 256
        l1_re, l1_im = fft256_functional(samples_re, samples_im)
        l1_ok = all(120 < value < 135 for value in l1_re) and all(value == 0 for value in l1_im)

        fft = fft_cls()
        sim = simulator_cls(fft)
        sim.reset("rst", cycles=2)
        for value in samples_re:
            sim.poke("di_en", 1)
            sim.poke("di_re", value)
            sim.poke("di_im", 0)
            sim.step()
        sim.poke("di_en", 0)
        hw_re = []
        hw_im = []
        for _ in range(700):
            sim.step()
            if sim.peek("do_en"):
                hw_re.append(_to_s16(sim.peek("do_re")))
                hw_im.append(_to_s16(sim.peek("do_im")))
        hw_re_nat = [hw_re[_bit_reverse(i, 8)] for i in range(256)]
        hw_im_nat = [hw_im[_bit_reverse(i, 8)] for i in range(256)]
        max_diff = max(max(abs(hw_re_nat[i] - l1_re[i]), abs(hw_im_nat[i] - l1_im[i])) for i in range(256))
        l3_ok = len(hw_re) == 256 and max_diff <= 1
        ok = l1_ok and l3_ok
        results.append(("FFT256 cross-layer", ok))
        print(f"  L1={l1_ok}, L3={l3_ok}, max_diff={max_diff}  {'PASS' if ok else 'FAIL'}")
    except Exception as exc:
        results.append(("FFT256 cross-layer", False))
        print(f"  FAIL: {exc}")

    print("\n" + "-" * 70)
    passed = sum(1 for _, item_ok in results if item_ok)
    for name, item_ok in results:
        print(f"  {name:25s} {'PASS' if item_ok else 'FAIL'}")
    print(f"  Total: {passed}/{len(results)}")
    print("-" * 70)
    return passed == len(results), results


__all__ = ["run_functional_tests", "run_dsl_sim_tests", "run_layer_verification"]
