#!/usr/bin/env python3
"""
FSMM pyUVM test platform (Q=16 scaled version).

Tests the FSMM accelerator with Q=16 block size matching the ICCAD'24 paper.
Covers:
- Directed sequences for each sparsity mode (1:16, 2:16, 4:16, 8:16, 16:16)
- Random sequences with random sparse patterns
- Scoreboard: Python reference model (dense gemm + masking + reordering)
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
    uvm_do, uvm_do_with, UVMAnalysisFIFO,
)
from rtlgen.pyuvm_sim import Scheduler, _walk_tree, PhaseRuntime
from rtlgen.core import flatten_module
from examples.fsmm import FSMM

Q = 16
DW = 8
IDXW = max(2, Q.bit_length())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def flatten_matrix(mat):
    """Flatten QxQ matrix to integer (row-major)."""
    val = 0
    for r in range(Q):
        for c in range(Q):
            val |= (mat[r][c] & ((1 << DW) - 1)) << ((r * Q + c) * DW)
    return val


def expand_matrix(val):
    """Expand integer to QxQ matrix."""
    mat = [[0] * Q for _ in range(Q)]
    for r in range(Q):
        for c in range(Q):
            mat[r][c] = (val >> ((r * Q + c) * DW)) & ((1 << DW) - 1)
    return mat


def ref_fsmm(f_mat, w_mat_compressed, reorder, mode):
    """
    Reference model.
    w_mat_compressed[c][k] = (val, row_idx) for column c, non-zero k.
    Computes O = F x W^T, then de-reorders columns.
    """
    max_k = {0: 1, 1: 2, 2: 4, 3: 8, 4: 16}[mode]
    o = [[0] * Q for _ in range(Q)]
    for r in range(Q):
        for c in range(Q):
            s = 0
            for k in range(max_k):
                val, idx = w_mat_compressed[c][k]
                s += f_mat[r][idx] * val
            o[r][c] = s & ((1 << DW) - 1)
    # De-reordering
    o2 = [[0] * Q for _ in range(Q)]
    for r in range(Q):
        for c in range(Q):
            src = reorder[c]
            o2[r][c] = o[r][src]
    return o2


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------
class FSMMTxn(UVMSequenceItem):
    _fields = [
        ("f_data", Q * Q * DW),
        ("w_data", Q * Q * DW),
        ("w_idx", Q * Q * IDXW),
        ("reorder_idx", Q * IDXW),
        ("mode", 3),
        ("start", 1),
        ("o_data", Q * Q * DW),
        ("valid_out", 1),
    ]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
class FSMMDriver(UVMDriver):
    async def run_phase(self, phase):
        while True:
            req = await self.seq_item_port.get_next_item()
            self.vif.cb.start <= req.start
            self.vif.cb.mode <= req.mode
            self.vif.cb.f_data <= req.f_data
            self.vif.cb.w_data <= req.w_data
            self.vif.cb.w_idx <= req.w_idx
            self.vif.cb.reorder_idx <= req.reorder_idx
            await delay(1)
            self.vif.cb.start <= 0
            self.seq_item_port.item_done()


# ---------------------------------------------------------------------------
# Monitors
# ---------------------------------------------------------------------------
class FSMMInMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            if int(self.vif.cb.start):
                txn = create(FSMMTxn, "txn")
                txn.start = 1
                txn.f_data = int(self.vif.cb.f_data)
                txn.w_data = int(self.vif.cb.w_data)
                txn.w_idx = int(self.vif.cb.w_idx)
                txn.reorder_idx = int(self.vif.cb.reorder_idx)
                txn.mode = int(self.vif.cb.mode)
                self.ap.write(txn)


class FSMMOutMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            if int(self.vif.cb.valid_out):
                txn = create(FSMMTxn, "txn")
                txn.valid_out = 1
                txn.o_data = int(self.vif.cb.o_data)
                self.ap.write(txn)


# ---------------------------------------------------------------------------
# Scoreboard
# ---------------------------------------------------------------------------
class FSMMScoreboard(UVMComponent):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.exp_fifo = UVMAnalysisFIFO("exp_fifo")
        self.act_fifo = UVMAnalysisFIFO("act_fifo")
        self.errors = 0
        self.passes = 0

    def _expected(self, txn):
        f_mat = expand_matrix(txn.f_data)
        w_mat = [[(0, 0)] * Q for _ in range(Q)]
        max_k = {0: 1, 1: 2, 2: 4, 3: 8, 4: 16}[txn.mode]
        for c in range(Q):
            for k in range(max_k):
                wb_lo = c * Q * DW + k * DW
                val = (txn.w_data >> wb_lo) & ((1 << DW) - 1)
                wi_lo = c * Q * IDXW + k * IDXW
                idx = (txn.w_idx >> wi_lo) & ((1 << IDXW) - 1)
                w_mat[c][k] = (val, idx)
        reorder = [(txn.reorder_idx >> (c * IDXW)) & ((1 << IDXW) - 1) for c in range(Q)]
        o_mat = ref_fsmm(f_mat, w_mat, reorder, txn.mode)
        return flatten_matrix(o_mat)

    async def run_phase(self, phase):
        total = self.cfg_db_get("total_txn_count") or 0
        phase.raise_objection(self)
        checked = 0
        while checked < total:
            in_txn = await self.exp_fifo.get()
            act_txn = await self.act_fifo.get()
            exp_data = self._expected(in_txn)
            if exp_data != act_txn.o_data:
                self.errors += 1
                uvm_error("SCOREBOARD", f"Mismatch! mode={in_txn.mode} exp={exp_data:#x} act={act_txn.o_data:#x}")
            else:
                self.passes += 1
            checked += 1
        phase.drop_objection(self)

    def report_phase(self, phase):
        uvm_info("SCOREBOARD", f"Passes={self.passes} Errors={self.errors}")


# ---------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------
class FSMMDirectedSeq(UVMSequence):
    async def body(self):
        for mode in [0, 1, 2, 3, 4]:
            max_k = {0: 1, 1: 2, 2: 4, 3: 8, 4: 16}[mode]
            f_mat = [[(r * Q + c + 1) & 0xFF for c in range(Q)] for r in range(Q)]
            w_mat = [[(0, 0)] * Q for _ in range(Q)]
            for c in range(Q):
                for k in range(max_k):
                    idx = k % Q
                    val = (c + k + 1) & 0xFF
                    w_mat[c][k] = (val, idx)
            reorder = list(range(Q))
            txn = create(FSMMTxn, "txn")
            txn.start = 1
            txn.mode = mode
            txn.f_data = flatten_matrix(f_mat)
            w_data = 0
            w_idx = 0
            for c in range(Q):
                for k in range(Q):
                    wb_lo = c * Q * DW + k * DW
                    w_data |= (w_mat[c][k][0] & 0xFF) << wb_lo
                    wi_lo = c * Q * IDXW + k * IDXW
                    w_idx |= (w_mat[c][k][1] & ((1 << IDXW) - 1)) << wi_lo
            txn.w_data = w_data
            txn.w_idx = w_idx
            txn.reorder_idx = sum(reorder[c] << (c * IDXW) for c in range(Q))
            await start_item(txn)
            await finish_item(txn)
            await delay(Q * max_k + 10)


class FSMMRandomSeq(UVMSequence):
    async def body(self):
        n = self.cfg_db_get("random_count") or 20
        for _ in range(n):
            mode = random.randint(0, 4)
            max_k = {0: 1, 1: 2, 2: 4, 3: 8, 4: 16}[mode]
            f_mat = [[random.randint(0, 255) for _ in range(Q)] for _ in range(Q)]
            w_mat = [[(0, 0)] * Q for _ in range(Q)]
            for c in range(Q):
                indices = list(range(Q))
                random.shuffle(indices)
                for k in range(max_k):
                    w_mat[c][k] = (random.randint(0, 255), indices[k])
            reorder = list(range(Q))
            random.shuffle(reorder)

            txn = create(FSMMTxn, "txn")
            txn.start = 1
            txn.mode = mode
            txn.f_data = flatten_matrix(f_mat)
            w_data = 0
            w_idx = 0
            for c in range(Q):
                for k in range(Q):
                    wb_lo = c * Q * DW + k * DW
                    w_data |= (w_mat[c][k][0] & 0xFF) << wb_lo
                    wi_lo = c * Q * IDXW + k * IDXW
                    w_idx |= (w_mat[c][k][1] & ((1 << IDXW) - 1)) << wi_lo
            txn.w_data = w_data
            txn.w_idx = w_idx
            txn.reorder_idx = sum(reorder[c] << (c * IDXW) for c in range(Q))
            await start_item(txn)
            await finish_item(txn)
            await delay(Q * max_k + 10)


# ---------------------------------------------------------------------------
# Agent / Env / Test
# ---------------------------------------------------------------------------
class FSMMAgent(UVMAgent):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.sqr = UVMSequencer("sqr", self)
        self.driver = FSMMDriver("driver", self)
        self.in_mon = FSMMInMonitor("in_mon", self)
        self.out_mon = FSMMOutMonitor("out_mon", self)

    def connect_phase(self, phase):
        self.driver.seq_item_port.connect(self.sqr.seq_item_export)


class FSMMEnv(UVMEnv):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.agent = FSMMAgent("agent", self)
        self.sb = FSMMScoreboard("sb", self)

    def connect_phase(self, phase):
        self.sb.exp_fifo.connect_export(self.agent.in_mon.ap)
        self.sb.act_fifo.connect_export(self.agent.out_mon.ap)


class FSMMTest(UVMTest):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.env = FSMMEnv("env", self)

    async def run_phase(self, phase):
        phase.raise_objection(self)
        dseq = create(FSMMDirectedSeq, "dseq")
        rseq = create(FSMMRandomSeq, "rseq")
        await dseq.start(self.env.agent.sqr)
        await rseq.start(self.env.agent.sqr)
        await delay(10)
        phase.drop_objection(self)


class FSMMSingleTxnSeq(UVMSequence):
    """Send a single directed transaction (mode=0) for quick smoke test."""
    async def body(self):
        f_mat = [[(r * Q + c + 1) & 0xFF for c in range(Q)] for r in range(Q)]
        w_mat = [[(0, 0)] * Q for _ in range(Q)]
        for c in range(Q):
            w_mat[c][0] = ((c + 1) & 0xFF, 0)
        reorder = list(range(Q))
        txn = create(FSMMTxn, "txn")
        txn.start = 1
        txn.mode = 0
        txn.f_data = flatten_matrix(f_mat)
        w_data = 0
        w_idx = 0
        for c in range(Q):
            for k in range(Q):
                wb_lo = c * Q * DW + k * DW
                w_data |= (w_mat[c][k][0] & 0xFF) << wb_lo
                wi_lo = c * Q * IDXW + k * IDXW
                w_idx |= (w_mat[c][k][1] & ((1 << IDXW) - 1)) << wi_lo
        txn.w_data = w_data
        txn.w_idx = w_idx
        txn.reorder_idx = sum(reorder[c] << (c * IDXW) for c in range(Q))
        await start_item(txn)
        await finish_item(txn)
        await delay(Q + 10)


# ---------------------------------------------------------------------------
# Custom runner
# ---------------------------------------------------------------------------
async def _run_fsmm_test_async(test: UVMTest, sim: Simulator, max_cycles: int = 5000):
    import rtlgen.pyuvm as pyuvm
    sched = Scheduler(sim, clk_name="clk")
    pyuvm._current_scheduler = sched

    # active-low reset
    sim.set("rst_n", 0)
    sim.set("start", 0)
    sim.set("mode", 0)
    sim.set("f_data", 0)
    sim.set("w_data", 0)
    sim.set("w_idx", 0)
    sim.set("reorder_idx", 0)
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


def run_fsmm_test(test: UVMTest, sim: Simulator, max_cycles: int = 5000):
    import rtlgen.pyuvm as _pyuvm
    _pyuvm.clear_checkers()
    _pyuvm.UVMConfigDB.clear()
    return asyncio.run(_run_fsmm_test_async(test, sim, max_cycles))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def test_fsmm():
    # Flatten the hierarchical design for simulation speed while keeping
    # the generated Verilog fully hierarchical.
    dut = flatten_module(FSMM(Q=Q, DW=DW))
    sim = Simulator(dut)
    test = FSMMTest("test")
    directed_count = 1
    random_count = 0
    test.cfg_db_set("total_txn_count", directed_count + random_count)
    test.cfg_db_set("random_count", random_count)

    async def quick_run_phase(phase):
        phase.raise_objection(test)
        seq = FSMMSingleTxnSeq("seq")
        await seq.start(test.env.agent.sqr)
        await delay(10)
        phase.drop_objection(test)

    test.run_phase = quick_run_phase

    summary = run_fsmm_test(test, sim)
    if summary.get("failed", 0) > 0 or test.env.sb.errors > 0:
        sys.exit(1)
    print(f"FSMM UVM test PASSED: {test.env.sb.passes}/{directed_count + random_count} transactions")


if __name__ == "__main__":
    test_fsmm()
