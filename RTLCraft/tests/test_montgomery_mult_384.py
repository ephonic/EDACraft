#!/usr/bin/env python3
"""
Unit tests for 384-bit Montgomery Modular Multiplier.

Covers:
- Functional correctness with directed and random vectors
- Verilog lint checking (auto-fix)
- AST-based PPA analysis
- ABC post-synthesis verification
"""

import sys
import random

sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator, VerilogEmitter
from rtlgen.ppa import PPAAnalyzer
from rtlgen.synth import ABCSynthesizer
from rtlgen.blifgen import BLIFEmitter
from examples.montgomery_mult_384 import MontgomeryMult384

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def egcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x1, y1 = egcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return g, x, y


def modinv(a, m):
    g, x, _ = egcd(a % m, m)
    if g != 1:
        return None
    return x % m


def ref_montgomery(X, Y, M, n=384):
    """Standard Montgomery reduction (matches hardware word-level algorithm)."""
    R = 1 << n
    T = X * Y
    M_prime = (-modinv(M, R)) % R
    q = (T * M_prime) & (R - 1)
    Z = (T + q * M) >> n
    if Z >= M:
        Z -= M
    return Z


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------
LATENCY = 60  # measured pipeline latency from i_valid to o_valid


def test_directed_vectors():
    """Directed test with a few hand-picked vectors."""
    M = (1 << 383) | 1
    Mp = (-modinv(M, 1 << 128)) % (1 << 128)

    vectors = [
        (1, 1),
        (2, 3),
        (M - 1, M - 1),
        (12345678901234567890123456789012345678901234567890 % M,
         98765432109876543210987654321098765432109876543210 % M),
    ]

    dut = MontgomeryMult384()
    sim = Simulator(dut)
    sim.reset('rst_n')
    sim.set("o_ready", 1)

    results = []
    for X, Y in vectors:
        sim.set("X", X)
        sim.set("Y", Y)
        sim.set("M", M)
        sim.set("M_prime", Mp)
        sim.set("i_valid", 1)
        sim.step()
        sim.set("i_valid", 0)
        for _ in range(LATENCY + 5):
            sim.step()
            if sim.get("o_valid"):
                results.append(sim.get("Z"))
                break

    assert len(results) == len(vectors)
    for i, (X, Y) in enumerate(vectors):
        expected = ref_montgomery(X, Y, M)
        assert results[i] == expected, f"vector {i}: expected {hex(expected)} got {hex(results[i])}"


def test_random_vectors():
    """Random test with 50 different moduli and operands."""
    random.seed(2024)
    dut = MontgomeryMult384()
    sim = Simulator(dut)
    sim.reset('rst_n')
    sim.set("o_ready", 1)

    inputs = []
    expected = []
    for _ in range(50):
        M = random.getrandbits(384) | 1
        M |= (1 << 383)
        X = random.randint(0, M - 1)
        Y = random.randint(0, M - 1)
        Mp = (-modinv(M, 1 << 128)) % (1 << 128)
        inputs.append((X, Y, M, Mp))
        expected.append(ref_montgomery(X, Y, M))

    results = []
    for X, Y, M, Mp in inputs:
        sim.set("X", X)
        sim.set("Y", Y)
        sim.set("M", M)
        sim.set("M_prime", Mp)
        sim.set("i_valid", 1)
        sim.step()
        if sim.get("o_valid"):
            results.append(sim.get("Z"))

    sim.set("i_valid", 0)
    for _ in range(LATENCY + 10):
        sim.step()
        if sim.get("o_valid"):
            results.append(sim.get("Z"))

    assert len(results) == len(expected)
    for i, (exp, act) in enumerate(zip(expected, results)):
        assert exp == act, f"random vector {i}: expected {hex(exp)} got {hex(act)}"


def test_back_to_back_throughput():
    """Verify 1 result per cycle throughput after initial latency."""
    random.seed(42)
    M = (1 << 383) | 1
    Mp = (-modinv(M, 1 << 128)) % (1 << 128)
    num = 20

    inputs = [(random.randint(0, M - 1), random.randint(0, M - 1)) for _ in range(num)]
    expected = [ref_montgomery(X, Y, M) for X, Y in inputs]

    dut = MontgomeryMult384()
    sim = Simulator(dut)
    sim.reset('rst_n')
    sim.set("o_ready", 1)

    # Feed inputs back-to-back
    for X, Y in inputs:
        sim.set("X", X)
        sim.set("Y", Y)
        sim.set("M", M)
        sim.set("M_prime", Mp)
        sim.set("i_valid", 1)
        sim.step()

    sim.set("i_valid", 0)
    results = []
    for _ in range(LATENCY + num + 5):
        sim.step()
        if sim.get("o_valid"):
            results.append(sim.get("Z"))

    assert len(results) == num, f"Expected {num} results, got {len(results)}"
    for i, (exp, act) in enumerate(zip(expected, results)):
        assert exp == act, f"back-to-back vector {i}: expected {hex(exp)} got {hex(act)}"


# ---------------------------------------------------------------------------
# Lint test
# ---------------------------------------------------------------------------
def test_lint():
    dut = MontgomeryMult384()
    emitter = VerilogEmitter()
    text, lint_result = emitter.emit_with_lint(dut, auto_fix=True)
    critical = [i for i in lint_result.issues if i.severity == "error"]
    assert len(critical) == 0, f"Lint errors: {[i.message for i in critical]}"
    assert "`default_nettype none" in text


# ---------------------------------------------------------------------------
# PPA analysis
# ---------------------------------------------------------------------------
def test_ppa_analysis():
    dut = MontgomeryMult384()
    analyzer = PPAAnalyzer(dut)
    static = analyzer.analyze_static()
    assert static["logic_depth"] is not None
    assert static["gate_count"] > 0
    assert static["reg_bits"] > 0
    suggestions = analyzer.suggest_optimizations(static)
    print(f"[PPA] logic_depth={max(static['logic_depth'].values())}, gate_count={static['gate_count']}, reg_bits={static['reg_bits']}")
    for s in suggestions:
        print(f"  {s}")


# ---------------------------------------------------------------------------
# Post-synthesis test
# ---------------------------------------------------------------------------
def test_abc_synthesis():
    dut = MontgomeryMult384()
    blif_gen = BLIFEmitter()
    blif_text = blif_gen.emit(dut)

    synth = ABCSynthesizer()
    if not synth.is_available():
        print("[SKIP] ABC not available")
        return

    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        blif_path = os.path.join(td, "mm384.blif")
        v_path = os.path.join(td, "mm384_mapped.v")
        with open(blif_path, "w") as f:
            f.write(blif_text)

        liberty = "/Users/yangfan/rtlgen/gf65.lib"
        result = synth.run(
            input_blif=blif_path,
            liberty=liberty if os.path.exists(liberty) else None,
            output_verilog=v_path,
            optimization="resyn2",
        )
        assert os.path.exists(v_path)
        print(f"[SYNTH] area={result.area:.1f} delay={result.delay:.1f} gates={result.num_gates}")


if __name__ == "__main__":
    test_directed_vectors()
    print("Directed vectors passed")
    test_random_vectors()
    print("Random vectors passed")
    test_back_to_back_throughput()
    print("Back-to-back throughput passed")
    test_lint()
    print("Lint passed")
    test_ppa_analysis()
    print("PPA analysis passed")
    test_abc_synthesis()
    print("ABC synthesis passed")
    print("\nAll tests passed!")
