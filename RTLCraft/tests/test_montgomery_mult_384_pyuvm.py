#!/usr/bin/env python3
"""
pyUVM testbench for 384-bit Montgomery Modular Multiplier.

Coverage strategy:
- Directed sequence: edge cases (1x1, max-1 x max-1, etc.)
- Random sequence: 100 random transactions with different moduli
- Scoreboard: Python reference model (standard Montgomery)
- Coverage: input magnitude ranges, M bit-width
"""

import asyncio
import random
import sys

sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from rtlgen.pyuvm import (
    UVMComponent, UVMSequenceItem, UVMSequence, UVMVirtualSequence, UVMSequencer,
    UVMDriver, UVMMonitor, UVMAgent, UVMEnv, UVMTest,
    uvm_fatal, uvm_info, uvm_error, create, delay, start_item, finish_item,
    randomize, uvm_do, uvm_do_with, Coverage,
    UVMAnalysisFIFO, UVMBlockingGetPort,
)
from rtlgen.pyuvm_sim import Scheduler, _walk_tree, PhaseRuntime
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
    R = 1 << n
    T = X * Y
    M_prime = (-modinv(M, R)) % R
    q = (T * M_prime) & (R - 1)
    Z = (T + q * M) >> n
    if Z >= M:
        Z -= M
    return Z


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------
class MontgomeryMultTxn(UVMSequenceItem):
    _fields = [
        ("X", 384),
        ("Y", 384),
        ("M", 384),
        ("M_prime", 128),
        ("Z", 384),
    ]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
class MontgomeryMultDriver(UVMDriver):
    async def run_phase(self, phase):
        while True:
            req = await self.seq_item_port.get_next_item()
            while not int(self.vif.cb.i_ready):
                await delay(1)
            self.vif.cb.i_valid <= 1
            self.vif.cb.X <= req.X
            self.vif.cb.Y <= req.Y
            self.vif.cb.M <= req.M
            self.vif.cb.M_prime <= req.M_prime
            await delay(1)
            self.vif.cb.i_valid <= 0
            self.seq_item_port.item_done()


# ---------------------------------------------------------------------------
# Monitors
# ---------------------------------------------------------------------------
class MontgomeryMultInMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            if int(self.vif.cb.i_valid) and int(self.vif.cb.i_ready):
                txn = create(MontgomeryMultTxn, "txn")
                txn.X = int(self.vif.cb.X)
                txn.Y = int(self.vif.cb.Y)
                txn.M = int(self.vif.cb.M)
                txn.M_prime = int(self.vif.cb.M_prime)
                self.ap.write(txn)


class MontgomeryMultOutMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            if int(self.vif.cb.o_valid) and int(self.vif.cb.o_ready):
                txn = create(MontgomeryMultTxn, "txn")
                txn.Z = int(self.vif.cb.Z)
                self.ap.write(txn)


# ---------------------------------------------------------------------------
# Scoreboard
# ---------------------------------------------------------------------------
class MontgomeryMultScoreboard(UVMComponent):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.total_txn_count = 104
        self.exp_fifo = UVMAnalysisFIFO("exp_fifo")
        self.act_fifo = UVMAnalysisFIFO("act_fifo")
        self.errors = 0
        self.passes = 0

        self.cov_x_range = Coverage("cov_x_range")
        self.cov_x_range.define_bins(["small", "mid", "large", "max"])
        self.cov_y_range = Coverage("cov_y_range")
        self.cov_y_range.define_bins(["small", "mid", "large", "max"])
        self.cov_m_msb = Coverage("cov_m_msb")
        self.cov_m_msb.define_bins(["lt256", "256to320", "320to384"])

    def _classify(self, val, bits):
        if val < (1 << (bits - 2)):
            return "small"
        if val < (1 << (bits - 1)):
            return "mid"
        if val < ((1 << bits) - (1 << (bits - 2))):
            return "large"
        return "max"

    def _classify_m(self, M):
        msb = M.bit_length()
        if msb < 256:
            return "lt256"
        if msb <= 320:
            return "256to320"
        return "320to384"

    async def run_phase(self, phase):
        phase.raise_objection(self)
        checked = 0
        while checked < self.total_txn_count:
            exp_txn = await self.exp_fifo.get()
            act_txn = await self.act_fifo.get()
            self._check(exp_txn, act_txn)
            checked += 1
        phase.drop_objection(self)

    def _check(self, exp_txn, act_txn):
        expected = ref_montgomery(exp_txn.X, exp_txn.Y, exp_txn.M)
        if expected == act_txn.Z:
            self.passes += 1
        else:
            self.errors += 1
            uvm_error("SB", f"Mismatch X={hex(exp_txn.X)} Y={hex(exp_txn.Y)} M={hex(exp_txn.M)} "
                            f"exp={hex(expected)} act={hex(act_txn.Z)}")

        self.cov_x_range.sample(self._classify(exp_txn.X, 384))
        self.cov_y_range.sample(self._classify(exp_txn.Y, 384))
        self.cov_m_msb.sample(self._classify_m(exp_txn.M))

    def report_phase(self, phase):
        print(f"[SCOREBOARD] passes={self.passes} errors={self.errors}")
        self.cov_x_range.report()
        self.cov_y_range.report()
        self.cov_m_msb.report()


# ---------------------------------------------------------------------------
# Agent / Env
# ---------------------------------------------------------------------------
class MontgomeryMultAgent(UVMAgent):
    def build_phase(self, phase):
        self.sqr = UVMSequencer("sqr", self)
        self.drv = MontgomeryMultDriver("drv", self)
        self.in_mon = MontgomeryMultInMonitor("in_mon", self)
        self.out_mon = MontgomeryMultOutMonitor("out_mon", self)

    def connect_phase(self, phase):
        self.drv.seq_item_port.connect(self.sqr.seq_item_export)


class MontgomeryMultEnv(UVMEnv):
    def build_phase(self, phase):
        self.agent = MontgomeryMultAgent("agent", self)
        self.sb = MontgomeryMultScoreboard("sb", self)

    def connect_phase(self, phase):
        self.sb.exp_fifo.connect_export(self.agent.in_mon.ap)
        self.sb.act_fifo.connect_export(self.agent.out_mon.ap)


# ---------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------
class MontgomeryMultDirectedSeq(UVMSequence):
    num_transactions = 4

    async def body(self):
        M = (1 << 383) | 1
        Mp = (-modinv(M, 1 << 128)) % (1 << 128)
        vectors = [
            (1, 1, M, Mp),
            (2, 3, M, Mp),
            (M - 1, M - 1, M, Mp),
            (12345678901234567890123456789012345678901234567890 % M,
             98765432109876543210987654321098765432109876543210 % M, M, Mp),
        ]
        for X, Y, M, Mp in vectors:
            txn = create(MontgomeryMultTxn, "txn")
            await uvm_do_with(txn, {"X": X, "Y": Y, "M": M, "M_prime": Mp})


class MontgomeryMultRandomSeq(UVMSequence):
    num_transactions = 100

    async def body(self):
        for _ in range(self.num_transactions):
            txn = create(MontgomeryMultTxn, "txn")
            M = random.getrandbits(384) | 1
            M |= (1 << 383)
            txn.M = M
            txn.M_prime = (-modinv(M, 1 << 128)) % (1 << 128)
            txn.X = random.randint(0, M - 1)
            txn.Y = random.randint(0, M - 1)
            await start_item(txn)
            await finish_item(txn)


class MontgomeryMultVSeq(UVMVirtualSequence):
    async def body(self):
        if self.p_sequencer is None:
            uvm_fatal("VSEQ", "p_sequencer is None")
        dseq = MontgomeryMultDirectedSeq("dseq")
        await dseq.start(self.p_sequencer, parent_sequence=self)
        rseq = MontgomeryMultRandomSeq("rseq")
        await rseq.start(self.p_sequencer, parent_sequence=self)
        total = dseq.num_transactions + rseq.num_transactions
        uvm_info("VSEQ", f"Total transactions = {total}", 0)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
class MontgomeryMultTest(UVMTest):
    def build_phase(self, phase):
        self.env = MontgomeryMultEnv("env", self)
        self.cfg_db_set("total_txn_count", 0)

    async def run_phase(self, phase):
        phase.raise_objection(self)
        total = 104
        self.cfg_db_set("total_txn_count", total)
        dseq = MontgomeryMultDirectedSeq("dseq")
        rseq = MontgomeryMultRandomSeq("rseq")
        await dseq.start(self.env.agent.sqr)
        await rseq.start(self.env.agent.sqr)
        await delay(20)
        phase.drop_objection(self)


# ---------------------------------------------------------------------------
# Custom runner
# ---------------------------------------------------------------------------
async def _run_mm_test_async(test: UVMTest, sim: Simulator, max_cycles: int = 5000):
    import rtlgen.pyuvm as pyuvm
    sched = Scheduler(sim)
    pyuvm._current_scheduler = sched

    sim.set("rst_n", 0)
    sim.set("i_valid", 0)
    sim.set("o_ready", 1)
    for _ in range(3):
        sched.step()
    sim.set("rst_n", 1)
    sched.step()

    phase = PhaseRuntime()

    def _build(comp):
        m = getattr(comp, "build_phase", None)
        if m:
            m(phase)
        for c in comp.children:
            _build(c)
    _build(test)

    def _bind_vif(comp):
        if hasattr(comp, "vif"):
            comp.vif = sched.vif
        for c in comp.children:
            _bind_vif(c)
    _bind_vif(test)
    test.cfg_db_set("vif", sched.vif)
    for comp in _walk_tree(test):
        if hasattr(comp, "vif") and getattr(comp, "vif", None) is None:
            v = comp.cfg_db_get("vif")
            if v:
                comp.vif = v

    def _connect(comp):
        m = getattr(comp, "connect_phase", None)
        if m:
            m(phase)
        for c in comp.children:
            _connect(c)
    _connect(test)

    tasks = []
    def _start_run(comp):
        m = getattr(comp, "run_phase", None)
        if m and asyncio.iscoroutinefunction(m):
            tasks.append(asyncio.create_task(m(phase)))
        for c in comp.children:
            _start_run(c)
    _start_run(test)

    while True:
        if phase.objection_count == 0:
            await asyncio.sleep(0)
            if phase.objection_count == 0:
                break
        if sched.cycle >= max_cycles:
            uvm_error("RUNNER", "Timeout!")
            break
        sched.step()
        await asyncio.sleep(0)

    for t in tasks:
        if not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

    for comp in _walk_tree(test):
        m = getattr(comp, "report_phase", None)
        if m:
            m(phase)

    summary = pyuvm.get_checker_summary()
    print(f"[CHECKER] total={summary['total']} passed={summary['passed']} failed={summary['failed']}")
    return summary


def run_mm_test(test: UVMTest, sim: Simulator, max_cycles: int = 5000):
    import rtlgen.pyuvm as _pyuvm
    _pyuvm.clear_checkers()
    _pyuvm.UVMConfigDB.clear()
    return asyncio.run(_run_mm_test_async(test, sim, max_cycles))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    dut = MontgomeryMult384()
    sim = Simulator(dut)
    test = MontgomeryMultTest("test")
    summary = run_mm_test(test, sim)
    if summary.get("failed", 0) > 0:
        sys.exit(1)
    print("\nMontgomeryMult384 pyUVM test completed successfully!")
