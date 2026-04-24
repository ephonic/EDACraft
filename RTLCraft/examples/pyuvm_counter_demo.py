#!/usr/bin/env python3
"""
pyUVM 原生框架示例：用纯 Python 描述 UVM 测试平台，然后一键生成 SV/UVM。
"""

import sys
sys.path.insert(0, "..")

from rtlgen.pyuvm import (
    UVMComponent, UVMSequenceItem, UVMSequence, UVMVirtualSequence, UVMSequencer,
    UVMDriver, UVMMonitor, UVMAgent, UVMEnv, UVMScoreboard,
    UVMTest, uvm_fatal, uvm_info, assert_eq, create, repeat, delay,
    start_item, finish_item, randomize, uvm_do, uvm_do_with, Coverage,
    UVMAnalysisFIFO, UVMBlockingGetPort,
    UVMRegField, UVMReg, UVMRegBlock, UVMRegPredictor,
)
from rtlgen.pyuvmgen import UVMEmitter as PyUVMEmitter
from counter import Counter


# -----------------------------------------------------------------
# Transaction
# -----------------------------------------------------------------
class CounterTxn(UVMSequenceItem):
    _fields = [
        ("en", 1),
        ("count", 8),
    ]


# -----------------------------------------------------------------
# Sequence
# -----------------------------------------------------------------
class CounterSubSeq(UVMSequence):
    """子 sequence：发送 num_transactions 个 txn，强制 en=1（uvm_do_with 示例）。"""
    num_transactions = 3

    async def body(self):
        for _ in repeat(self.num_transactions):
            txn = create(CounterTxn, "txn")
            await uvm_do_with(txn, {"en": 1})


class CounterSeq(UVMSequence):
    num_transactions = 5

    def pre_body(self):
        uvm_info("SEQ", "CounterSeq pre_body", 0)

    async def body(self):
        for _ in repeat(self.num_transactions):
            txn = create(CounterTxn, "txn")
            await uvm_do(txn)

    def post_body(self):
        uvm_info("SEQ", "CounterSeq post_body", 0)


class CounterVirtualSeq(UVMVirtualSequence):
    """Virtual sequence：启动 CounterSubSeq 和 CounterSeq。"""

    async def body(self):
        if self.p_sequencer is None:
            uvm_fatal("VSEQ", "p_sequencer is None")
        uvm_info("VSEQ", "Starting CounterSubSeq", 0)
        sub_seq = CounterSubSeq("sub_seq")
        await sub_seq.start(self.p_sequencer, parent_sequence=self)
        uvm_info("VSEQ", "CounterSubSeq done, starting CounterSeq", 0)
        seq = CounterSeq("seq")
        await seq.start(self.p_sequencer, parent_sequence=self)
        uvm_info("VSEQ", "CounterSeq done", 0)


# -----------------------------------------------------------------
# Driver
# -----------------------------------------------------------------
class CounterDriver(UVMDriver):
    def __init__(self, name, parent=None):
        super().__init__(name, parent, txn_type=CounterTxn)

    async def run_phase(self, phase):
        while True:
            self.req = await self.seq_item_port.get_next_item()
            await delay(1)
            self.vif.cb.en <= self.req.en
            self.seq_item_port.item_done()


# -----------------------------------------------------------------
# Monitor
# -----------------------------------------------------------------
class CounterMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            txn = create(CounterTxn, "txn")
            txn.en = int(self.vif.cb.en)
            txn.count = int(self.vif.cb.count)
            self.ap.write(txn)


# -----------------------------------------------------------------
# Agent
# -----------------------------------------------------------------
class CounterAgent(UVMAgent):
    def build_phase(self, phase):
        self.sqr = UVMSequencer("sqr", self)
        self.drv = CounterDriver("drv", self)
        self.mon = CounterMonitor("mon", self)

    def connect_phase(self, phase):
        self.drv.seq_item_port.connect(self.sqr.seq_item_export)


# -----------------------------------------------------------------
# Scoreboard
# -----------------------------------------------------------------
class CounterScoreboard(UVMScoreboard):
    def __init__(self, name, parent=None):
        super().__init__(name, parent, txn_type=CounterTxn)
        self.expect_count = 0
        self.golden_count = 0
        self.cov = Coverage("en_cov")
        self.cov.define_bins([0, 1])
        self.afifo = UVMAnalysisFIFO("afifo", maxsize=64)
        self.get_port = UVMBlockingGetPort("get_port")
        self.ral: Optional[UVMRegBlock] = None

    def build_phase(self, phase):
        self.afifo.connect_get_port(self.get_port)
        self.ral = self.uvm_config_db_get("ral")

    async def run_phase(self, phase):
        while True:
            txn = await self.get_port.get()
            self.expect_count += 1
            self.cov.sample(txn.en)
            # 若存在 RAL，用 mirror 值做额外断言
            if self.ral is not None:
                mirror_en = self.ral.read_reg(0x00) & 0x1
                uvm_info("SCB", f"Txn #{self.expect_count} en={txn.en} count={txn.count} ral_en={mirror_en}", 0)
                assert_eq(int(txn.en), mirror_en, "en vs RAL mismatch")
            else:
                uvm_info("SCB", f"Txn #{self.expect_count} en={txn.en} count={txn.count}", 0)
            if txn.en:
                self.golden_count += 1
            assert_eq(int(txn.count), self.golden_count, "count mismatch")

    def report_phase(self, phase):
        self.cov.report()


# -----------------------------------------------------------------
# Environment
# -----------------------------------------------------------------
class CounterRegBlock(UVMRegBlock):
    """Counter 的 RAL 模型：0x00 ctrl [en@bit0]。"""
    def __init__(self, name="ral", parent=None):
        super().__init__(name, parent)
        ctrl = UVMReg("ctrl", width=8, reset=0)
        ctrl.add_field(UVMRegField("en", width=1, lsb_pos=0, access="RW", reset=0))
        self.add_reg(ctrl, offset=0x00)


class CounterEnv(UVMEnv):
    def build_phase(self, phase):
        self.agent = CounterAgent("agent", self)
        self.sb = CounterScoreboard("sb", self)
        self.ral = CounterRegBlock("ral", self)
        self.predictor = UVMRegPredictor("predictor", self, reg_block=self.ral)
        self.uvm_config_db_set("ral", self.ral)

    def connect_phase(self, phase):
        self.agent.mon.ap.connect(self.sb.afifo)
        self.agent.mon.ap.connect(self.predictor.exp)


# -----------------------------------------------------------------
# Test
# -----------------------------------------------------------------
class CounterTest(UVMTest):
    def __init__(self, name, dut):
        super().__init__(name)
        self.dut = dut

    def build_phase(self, phase):
        self.env = CounterEnv("env", self)

    async def run_phase(self, phase):
        phase.raise_objection(self)
        vseq = CounterVirtualSeq("vseq")
        await vseq.start(self.env.agent.sqr, starting_phase=phase)
        # 等待足够周期让 monitor/scoreboard 处理完剩余事务
        await delay(10)
        phase.drop_objection(self)


# -----------------------------------------------------------------
# Main
# -----------------------------------------------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        from rtlgen.sim import Simulator
        from rtlgen.pyuvm_sim import run_test

        dut = Counter(width=8)
        sim = Simulator(dut)
        test = CounterTest("counter_test", dut)
        run_test(test, sim, max_cycles=100)
        print("[pyuvm] Python runtime simulation finished.")
    else:
        dut = Counter(width=8)
        test = CounterTest("counter_test", dut)
        files = PyUVMEmitter().emit(test, pkg_name="counter_test_pkg")

        for fname, content in files.items():
            print(f"// {'='*60}")
            print(f"// File: {fname}")
            print(f"// {'='*60}")
            print(content)
            print()
