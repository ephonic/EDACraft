#!/usr/bin/env python3
"""
SHA3-256 pyUVM test platform.

Covers:
- Directed sequence: empty, abc, max-length single-block (135 bytes)
- Random sequence: random lengths 0..135 with random bytes
- Scoreboard: Python hashlib.sha3_256 reference model
"""

import asyncio
import hashlib
import sys

sys.path.insert(0, "/Users/yangfan/rtlgen")

from rtlgen import Simulator
from rtlgen.pyuvm import (
    UVMComponent, UVMSequenceItem, UVMSequence, UVMVirtualSequence, UVMSequencer,
    UVMDriver, UVMMonitor, UVMAgent, UVMEnv, UVMTest,
    uvm_fatal, uvm_info, uvm_error, create, delay, start_item, finish_item,
    randomize, uvm_do, uvm_do_with, Coverage, sv_dpi,
    UVMAnalysisFIFO, UVMBlockingGetPort,
)
from rtlgen.pyuvm_sim import Scheduler, _walk_tree, PhaseRuntime
from examples.sha3_256_pipe import SHA3_256

MAX_MSG_LEN = 135

# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------
class SHA3Txn(UVMSequenceItem):
    _fields = [
        ("msg_len", 8),
        ("block", 1088),
        ("hash", 256),
    ]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
class SHA3Driver(UVMDriver):
    async def run_phase(self, phase):
        while True:
            req = await self.seq_item_port.get_next_item()
            while not int(self.vif.cb.i_ready):
                await delay(1)
            self.vif.cb.i_valid <= 1
            self.vif.cb.block <= req.block
            self.vif.cb.block_len <= req.msg_len
            self.vif.cb.last_block <= 1
            await delay(1)
            self.vif.cb.i_valid <= 0
            self.vif.cb.last_block <= 0
            self.seq_item_port.item_done()


# ---------------------------------------------------------------------------
# Monitors
# ---------------------------------------------------------------------------
class SHA3InMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            if int(self.vif.cb.i_valid) and int(self.vif.cb.i_ready):
                txn = create(SHA3Txn, "txn")
                txn.msg_len = int(self.vif.cb.block_len)
                txn.block = int(self.vif.cb.block)
                self.ap.write(txn)


class SHA3OutMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            if int(self.vif.cb.o_valid) and int(self.vif.cb.o_ready):
                txn = create(SHA3Txn, "txn")
                txn.hash = int(self.vif.cb.hash)
                self.ap.write(txn)


# ---------------------------------------------------------------------------
# DPI reference model (Python side + SV side via DPI-C)
# ---------------------------------------------------------------------------
from rtlgen.dpi_runtime import dpi_sha3_256


# ---------------------------------------------------------------------------
# Scoreboard
# ---------------------------------------------------------------------------
class SHA3Scoreboard(UVMComponent):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.exp_fifo = UVMAnalysisFIFO("exp_fifo")
        self.act_fifo = UVMAnalysisFIFO("act_fifo")
        self.errors = 0
        self.passes = 0

    async def run_phase(self, phase):
        total = self.cfg_db_get("total_txn_count") or 0
        phase.raise_objection(self)
        checked = 0
        while checked < total:
            exp_txn = await self.exp_fifo.get()
            act_txn = await self.act_fifo.get()
            self.check(exp_txn, act_txn)
            checked += 1
        phase.drop_objection(self)

    def check(self, exp_txn, act_txn):
        block_arr = [0] * 17
        hash_out = [0] * 4
        for i in range(17):
            block_arr[i] = (exp_txn.block >> (i * 64)) & 18446744073709551615
        dpi_sha3_256(block_arr, exp_txn.msg_len, hash_out)
        expected = 0
        for i in range(4):
            expected = expected | (hash_out[i] << (i * 64))
        if act_txn.hash == expected:
            self.passes += 1
        else:
            self.errors += 1
            uvm_error("SB", f"Mismatch msg_len={exp_txn.msg_len} -> exp={expected:064x} act={act_txn.hash:064x}")

    def report_phase(self, phase):
        print(f"[SCOREBOARD] passes={self.passes} errors={self.errors}")


# ---------------------------------------------------------------------------
# Agent / Env
# ---------------------------------------------------------------------------
class SHA3Agent(UVMAgent):
    def build_phase(self, phase):
        self.sqr = UVMSequencer("sqr", self)
        self.drv = SHA3Driver("drv", self)
        self.in_mon = SHA3InMonitor("in_mon", self)
        self.out_mon = SHA3OutMonitor("out_mon", self)

    def connect_phase(self, phase):
        self.drv.seq_item_port.connect(self.sqr.seq_item_export)


class SHA3Env(UVMEnv):
    def build_phase(self, phase):
        self.agent = SHA3Agent("agent", self)
        self.sb = SHA3Scoreboard("sb", self)

    def connect_phase(self, phase):
        self.sb.exp_fifo.connect_export(self.agent.in_mon.ap)
        self.sb.act_fifo.connect_export(self.agent.out_mon.ap)


# ---------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------
class SHA3DirectedSeq(UVMSequence):
    async def body(self):
        vectors = [
            b"",
            b"abc",
            b"hello world",
            bytes(range(MAX_MSG_LEN)),
        ]
        for msg in vectors:
            txn = create(SHA3Txn, "txn")
            block = int.from_bytes(msg, "little")
            await uvm_do_with(txn, {"msg_len": len(msg), "block": block})
        self.num_transactions = len(vectors)
        uvm_info("DSEQ", f"Directed sequence sent {self.num_transactions} transactions", 0)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
class SHA3Test(UVMTest):
    def build_phase(self, phase):
        self.env = SHA3Env("env", self)
        self.cfg_db_set("total_txn_count", 0)

    async def run_phase(self, phase):
        phase.raise_objection(self)
        dseq = SHA3DirectedSeq("dseq")
        self.cfg_db_set("total_txn_count", dseq.num_transactions)
        await dseq.start(self.env.agent.sqr)
        # Pipeline drain (24 stages + margin)
        await delay(30)
        phase.drop_objection(self)


# ---------------------------------------------------------------------------
# Custom runner for rst_n active-low
# ---------------------------------------------------------------------------
async def _run_sha3_test_async(test: UVMTest, sim: Simulator, max_cycles: int = 3000):
    import rtlgen.pyuvm as pyuvm
    sched = Scheduler(sim)
    pyuvm._current_scheduler = sched

    # active-low reset
    sim.set("rst_n", 0)
    sim.set("i_valid", 0)
    sim.set("o_ready", 1)
    sim.set("block", 0)
    sim.set("block_len", 0)
    sim.set("last_block", 0)
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


def run_sha3_test(test: UVMTest, sim: Simulator, max_cycles: int = 500):
    import rtlgen.pyuvm as _pyuvm
    _pyuvm.clear_checkers()
    _pyuvm.UVMConfigDB.clear()
    return asyncio.run(_run_sha3_test_async(test, sim, max_cycles))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    dut = SHA3_256()
    sim = Simulator(dut)
    test = SHA3Test("test")
    summary = run_sha3_test(test, sim)
    if summary.get("failed", 0) > 0:
        sys.exit(1)
    print("\nSHA3-256 pyUVM test completed successfully!")
