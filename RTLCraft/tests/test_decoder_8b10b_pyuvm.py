#!/usr/bin/env python3
import asyncio
import random
import sys

sys.path.insert(0, "/home/yangfan/EDAClaw/rtlgen")

from rtlgen import Simulator
from rtlgen.pyuvm import (
    UVMComponent, UVMSequenceItem, UVMSequence, UVMSequencer,
    UVMDriver, UVMMonitor, UVMAgent, UVMEnv, UVMTest,
    uvm_fatal, uvm_info, uvm_error, create, delay, start_item, finish_item,
    uvm_do, uvm_do_with, UVMAnalysisFIFO, Coverage,
)
from rtlgen.pyuvm_sim import Scheduler, _walk_tree, PhaseRuntime
from rtlgen.dpi_runtime import dpi_decoder_8b10b_ref
from examples.decoder_8b10b import Decoder8b10b, CONTROL_TABLE, DATA5_TABLE, DATA3_TABLE


def _build_ref_luts():
    d5 = {}
    for pat, val in DATA5_TABLE:
        d5[pat] = val
    d3 = {}
    for pat, val in DATA3_TABLE:
        d3[pat] = val
    data_lut = {}
    for upper in range(1 << 6):
        for lower in range(1 << 4):
            ten = (upper << 4) | lower
            if upper in d5 and lower in d3:
                data_lut[ten] = (d3[lower] << 5) | d5[upper]
    ctrl_lut = {}
    for pat, val in CONTROL_TABLE:
        ctrl_lut[pat] = val
    return data_lut, ctrl_lut


DATA_LUT, CONTROL_LUT = _build_ref_luts()
VALID_UPPER = sorted({p for p, _ in DATA5_TABLE})
VALID_LOWER = sorted({p for p, _ in DATA3_TABLE})
CONTROL_PATTERNS = sorted({p for p, _ in CONTROL_TABLE})


class DecoderTxn(UVMSequenceItem):
    _fields = [
        ("decoder_in", 10),
        ("control_in", 1),
        ("decoder_valid_in", 1),
        ("decoder_out", 8),
        ("control_out", 1),
        ("decoder_valid_out", 1),
    ]


class DecoderDriver(UVMDriver):
    async def run_phase(self, phase):
        while True:
            req = await self.seq_item_port.get_next_item()
            self.vif.cb.control_in <= req.control_in
            self.vif.cb.decoder_in <= req.decoder_in
            self.vif.cb.decoder_valid_in <= req.decoder_valid_in
            await delay(1)
            self.seq_item_port.item_done()


class DecoderInMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            if int(self.vif.cb.decoder_valid_in):
                txn = create(DecoderTxn, "txn")
                txn.decoder_in = int(self.vif.cb.decoder_in)
                txn.control_in = int(self.vif.cb.control_in)
                txn.decoder_valid_in = 1
                self.ap.write(txn)


class DecoderOutMonitor(UVMMonitor):
    async def run_phase(self, phase):
        while True:
            await delay(1)
            if int(self.vif.cb.decoder_valid_out):
                txn = create(DecoderTxn, "txn")
                txn.decoder_out = int(self.vif.cb.decoder_out)
                txn.control_out = int(self.vif.cb.control_out)
                txn.decoder_valid_out = 1
                self.ap.write(txn)


class DecoderScoreboard(UVMComponent):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.exp_fifo = UVMAnalysisFIFO("exp_fifo")
        self.act_fifo = UVMAnalysisFIFO("act_fifo")
        self.errors = 0
        self.passes = 0

        self.cov_control = Coverage("cov_control")
        self.cov_control.define_bins(CONTROL_PATTERNS + ["invalid_ctrl"])

        self.cov_data_upper = Coverage("cov_data_upper")
        self.cov_data_upper.define_bins(VALID_UPPER + ["invalid_upper"])

        self.cov_data_lower = Coverage("cov_data_lower")
        self.cov_data_lower.define_bins(VALID_LOWER + ["invalid_lower"])

        self.cov_data_full = Coverage("cov_data_full")
        valid_data = list(DATA_LUT.keys())
        invalid_data = [i for i in range(1 << 10) if i not in DATA_LUT and i not in CONTROL_LUT]
        sampled_invalid = invalid_data[:64] if len(invalid_data) > 64 else invalid_data
        self.cov_data_full.define_bins(valid_data + sampled_invalid + ["other_invalid"])

        self.cov_cross_ctrl_data = Coverage("cov_cross_ctrl_data")
        self.cov_cross_ctrl_data.define_bins([("/control/",), ("/data/",), ("/invalid/",)])

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
        out_arr = [0]
        ctrl_arr = [0]
        dpi_decoder_8b10b_ref(exp_txn.decoder_in, exp_txn.control_in, out_arr, ctrl_arr)
        expected_out = out_arr[0]
        expected_ctrl = ctrl_arr[0]

        if exp_txn.control_in == 1:
            if exp_txn.decoder_in in CONTROL_LUT:
                self.cov_control.sample(exp_txn.decoder_in)
                self.cov_cross_ctrl_data.sample(("/control/",))
            else:
                self.cov_control.sample("invalid_ctrl")
                self.cov_cross_ctrl_data.sample(("/invalid/",))
        else:
            upper = (exp_txn.decoder_in >> 4) & 0x3F
            lower = exp_txn.decoder_in & 0xF
            if upper in {p for p, _ in DATA5_TABLE}:
                self.cov_data_upper.sample(upper)
            else:
                self.cov_data_upper.sample("invalid_upper")
            if lower in {p for p, _ in DATA3_TABLE}:
                self.cov_data_lower.sample(lower)
            else:
                self.cov_data_lower.sample("invalid_lower")

            if exp_txn.decoder_in in DATA_LUT:
                self.cov_data_full.sample(exp_txn.decoder_in)
                self.cov_cross_ctrl_data.sample(("/data/",))
            elif exp_txn.decoder_in in self.cov_data_full.hits:
                self.cov_data_full.sample(exp_txn.decoder_in)
                self.cov_cross_ctrl_data.sample(("/invalid/",))
            else:
                self.cov_data_full.sample("other_invalid")
                self.cov_cross_ctrl_data.sample(("/invalid/",))

        if act_txn.decoder_out == expected_out and act_txn.control_out == expected_ctrl:
            self.passes += 1
        else:
            self.errors += 1
            uvm_error(
                "SB",
                f"Mismatch in=0b{exp_txn.decoder_in:010b} ctrl={exp_txn.control_in} "
                f"exp_out=0b{expected_out:08b} exp_ctrl={expected_ctrl} "
                f"act_out=0b{act_txn.decoder_out:08b} act_ctrl={act_txn.control_out}",
            )

    def report_phase(self, phase):
        print(f"[SCOREBOARD] passes={self.passes} errors={self.errors}")
        self.cov_control.report()
        self.cov_data_upper.report()
        self.cov_data_lower.report()
        self.cov_data_full.report()
        self.cov_cross_ctrl_data.report()


class DecoderAgent(UVMAgent):
    def build_phase(self, phase):
        self.sqr = UVMSequencer("sqr", self)
        self.drv = DecoderDriver("drv", self)
        self.in_mon = DecoderInMonitor("in_mon", self)
        self.out_mon = DecoderOutMonitor("out_mon", self)

    def connect_phase(self, phase):
        self.drv.seq_item_port.connect(self.sqr.seq_item_export)


class DecoderEnv(UVMEnv):
    def build_phase(self, phase):
        self.agent = DecoderAgent("agent", self)
        self.sb = DecoderScoreboard("sb", self)

    def connect_phase(self, phase):
        self.sb.exp_fifo.connect_export(self.agent.in_mon.ap)
        self.sb.act_fifo.connect_export(self.agent.out_mon.ap)


class DecoderDirectedSeq(UVMSequence):
    _txns = None

    @classmethod
    def _get_txns(cls):
        if cls._txns is not None:
            return cls._txns
        txns = []
        for pat, val in CONTROL_LUT.items():
            txns.append({"decoder_in": pat, "control_in": 1, "decoder_valid_in": 1})
        samples = [
            (0b100111_0100, 0),
            (0b011000_1011, 0),
            (0b110001_0011, 0),
            (0b111000_1110, 0),
            (0b101011_0001, 0),
            (0b000000_0000, 0),
        ]
        for pat, ctrl in samples:
            txns.append({"decoder_in": pat, "control_in": ctrl, "decoder_valid_in": 1})
        txns.append({"decoder_in": 0b000000_0000, "control_in": 1, "decoder_valid_in": 1})
        cls._txns = txns
        return txns

    async def body(self):
        for t in self._get_txns():
            txn = create(DecoderTxn, "txn")
            await uvm_do_with(txn, t)
        self.num_transactions = len(self._get_txns())
        uvm_info("DSEQ", f"Directed sequence sent {self.num_transactions} transactions", 0)


class DecoderCoverageSeq(UVMSequence):
    async def body(self):
        count = 0
        for upper in VALID_UPPER:
            for lower in VALID_LOWER:
                txn = create(DecoderTxn, "txn")
                await uvm_do_with(txn, {
                    "decoder_in": (upper << 4) | lower,
                    "control_in": 0,
                    "decoder_valid_in": 1,
                })
                count += 1
        uvm_info("CSEQ", f"Coverage sequence sent {count} transactions", 0)


class DecoderRandomSeq(UVMSequence):
    count = 100

    async def body(self):
        for _ in range(self.count):
            txn = create(DecoderTxn, "txn")
            mode = random.randint(0, 3)
            if mode == 0:
                txn.decoder_in = random.choice(CONTROL_PATTERNS)
                txn.control_in = 1
            elif mode == 1:
                upper = random.choice(VALID_UPPER)
                lower = random.choice(VALID_LOWER)
                txn.decoder_in = (upper << 4) | lower
                txn.control_in = 0
            elif mode == 2:
                txn.decoder_in = random.randint(0, (1 << 10) - 1)
                while txn.decoder_in in CONTROL_LUT:
                    txn.decoder_in = random.randint(0, (1 << 10) - 1)
                txn.control_in = 1
            else:
                txn.decoder_in = random.randint(0, (1 << 10) - 1)
                while txn.decoder_in in DATA_LUT or txn.decoder_in in CONTROL_LUT:
                    txn.decoder_in = random.randint(0, (1 << 10) - 1)
                txn.control_in = 0
            txn.decoder_valid_in = 1
            await uvm_do_with(txn, {"decoder_in": txn.decoder_in, "control_in": txn.control_in, "decoder_valid_in": 1})
        uvm_info("RSEQ", f"Random sequence sent {self.count} transactions", 0)


class DecoderTest(UVMTest):
    def __init__(self, name, dut=None):
        super().__init__(name)
        self.dut = dut

    def build_phase(self, phase):
        self.env = DecoderEnv("env", self)
        total = len(DecoderDirectedSeq._get_txns()) + len(VALID_UPPER) * len(VALID_LOWER) + DecoderRandomSeq.count
        self.cfg_db_set("total_txn_count", total)

    async def run_phase(self, phase):
        phase.raise_objection(self)
        dseq = DecoderDirectedSeq("dseq")
        await dseq.start(self.env.agent.sqr)
        cseq = DecoderCoverageSeq("cseq")
        await cseq.start(self.env.agent.sqr)
        rseq = DecoderRandomSeq("rseq")
        await rseq.start(self.env.agent.sqr)
        await delay(5)
        phase.drop_objection(self)


async def _run_decoder_test_async(test, sim, max_cycles=5000):
    import rtlgen.pyuvm as pyuvm
    sched = Scheduler(sim, clk_name="clk_in")
    pyuvm._current_scheduler = sched

    sim.set("reset_in", 1)
    sim.set("control_in", 0)
    sim.set("decoder_in", 0)
    sim.set("decoder_valid_in", 0)
    for _ in range(3):
        sched.step()
    sim.set("reset_in", 0)
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


def run_decoder_test(test, sim, max_cycles=5000):
    import rtlgen.pyuvm as _pyuvm
    _pyuvm.clear_checkers()
    _pyuvm.UVMConfigDB.clear()
    return asyncio.run(_run_decoder_test_async(test, sim, max_cycles))


if __name__ == "__main__":
    dut = Decoder8b10b()
    sim = Simulator(dut)
    test = DecoderTest("test", dut=dut)
    summary = run_decoder_test(test, sim)
    if summary.get("failed", 0) > 0:
        sys.exit(1)
    print("\n8b10b Decoder pyUVM test completed successfully!")
