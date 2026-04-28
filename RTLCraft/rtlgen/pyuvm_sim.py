"""
rtlgen.pyuvm_sim — Python UVM 运行时引擎

在 rtlgen.sim.Simulator 之上提供轻量级 UVM 运行时，支持：
- 协程调度（delay / await）
- Virtual Interface + ClockingBlock（NBA 赋值 <=）
- TLM 端口（seq_item_port / analysis_port）
- Phase / Objection 控制
"""
import asyncio
from typing import Any, Dict, List

from rtlgen.sim import Simulator
from rtlgen import pyuvm


class PhaseRuntime(pyuvm.UVMPhase):
    def __init__(self):
        self.objection_count = 0
        self._event = asyncio.Event()
        self._event.set()

    def raise_objection(self, obj: Any):
        if self.objection_count == 0:
            self._event.clear()
        self.objection_count += 1

    def drop_objection(self, obj: Any):
        self.objection_count -= 1
        if self.objection_count <= 0:
            self.objection_count = 0
            self._event.set()

    async def wait_for_drop(self):
        await self._event.wait()


class _CBSignal:
    def __init__(self, vif: "VirtualInterface", name: str):
        self.vif = vif
        self.name = name

    def __le__(self, value: Any):
        self.vif._schedule_drive(self.name, int(value))

    def __int__(self) -> int:
        return self.vif._read(self.name)

    def __eq__(self, other: Any) -> bool:
        return int(self) == other

    def __ne__(self, other: Any) -> bool:
        return int(self) != other

    def __lt__(self, other: Any) -> bool:
        return int(self) < other

    def __gt__(self, other: Any) -> bool:
        return int(self) > other

    def __ge__(self, other: Any) -> bool:
        return int(self) >= other

    def __add__(self, other: Any):
        return int(self) + int(other)

    def __sub__(self, other: Any):
        return int(self) - int(other)

    def __mul__(self, other: Any):
        return int(self) * int(other)

    def __repr__(self):
        return f"_CBSignal({self.name}={int(self)})"


class ClockingBlock:
    def __init__(self, vif: "VirtualInterface"):
        self.vif = vif

    def __getattr__(self, name: str):
        return _CBSignal(self.vif, name)


class VirtualInterface:
    def __init__(self, sim: Simulator, clk_name: str = "clk"):
        self.sim = sim
        self.clk = clk_name
        self.cb = ClockingBlock(self)
        self._drive_queue: Dict[str, int] = {}

    def _schedule_drive(self, name: str, value: int):
        self._drive_queue[name] = value

    def _apply_drive(self):
        for name, value in self._drive_queue.items():
            self.sim.set(name, value)
        self._drive_queue.clear()

    def _read(self, name: str) -> int:
        return self.sim.get_int(name)


class Scheduler:
    def __init__(self, sim: Simulator, clk_name: str = "clk"):
        self.sim = sim
        self.vif = VirtualInterface(sim, clk_name)
        self.cycle = 0
        self._waiters: List[Any] = []

    async def wait_cycles(self, n: int = 1):
        target = self.cycle + n
        if target <= self.cycle:
            return
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self._waiters.append((target, fut))
        await fut

    def step(self):
        self.cycle += 1
        self.vif._apply_drive()
        self.sim.step(do_trace=True)
        remaining = []
        for target, fut in self._waiters:
            if target <= self.cycle and not fut.done():
                fut.set_result(None)
            else:
                remaining.append((target, fut))
        self._waiters = remaining


def _walk_tree(root: pyuvm.UVMComponent) -> List[pyuvm.UVMComponent]:
    result = [root]
    for child in root.children:
        result.extend(_walk_tree(child))
    return result


async def run_test_async(test: pyuvm.UVMTest, sim: Simulator, max_cycles: int = 1000):
    sched = Scheduler(sim)
    pyuvm._current_scheduler = sched

    def _bind_vif(comp):
        if hasattr(comp, "vif"):
            comp.vif = sched.vif
        for child in list(comp.children):
            _bind_vif(child)

    # default reset
    sim.set("rst", 1)
    sim.set("en", 0)
    for _ in range(2):
        sched.step()
    sim.set("rst", 0)
    for _ in range(1):
        sched.step()

    phase = PhaseRuntime()

    # build_phase (sync, recursive)
    def _build(comp):
        m = getattr(comp, "build_phase", None)
        if m is not None:
            m(phase)
        for child in list(comp.children):
            _build(child)

    _build(test)

    # bind vif after hierarchy is fully built
    def _bind_vif(comp):
        if hasattr(comp, "vif"):
            comp.vif = sched.vif
        for child in list(comp.children):
            _bind_vif(child)

    _bind_vif(test)

    # connect_phase (sync, recursive)
    def _connect(comp):
        m = getattr(comp, "connect_phase", None)
        if m is not None:
            m(phase)
        for child in list(comp.children):
            _connect(child)

    _connect(test)

    # bind vif via config_db (UVM style)
    test.cfg_db_set("vif", sched.vif)
    for comp in _walk_tree(test):
        if hasattr(comp, "vif") and getattr(comp, "vif") is None:
            v = comp.cfg_db_get("vif")
            if v is not None:
                comp.vif = v

    # run_phase: start all async run_phase tasks (recursive)
    tasks = []
    def _start_run(comp):
        m = getattr(comp, "run_phase", None)
        if m is not None and asyncio.iscoroutinefunction(m):
            tasks.append(asyncio.create_task(m(phase)))
        for child in list(comp.children):
            _start_run(child)

    _start_run(test)

    # clock driver: step simulator until objections drop
    while True:
        if phase.objection_count == 0:
            await asyncio.sleep(0)
            if phase.objection_count == 0:
                break
        if sched.cycle >= max_cycles:
            break
        sched.step()
        await asyncio.sleep(0)

    # cancel remaining tasks
    for t in tasks:
        if not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

    # report_phase
    for comp in _walk_tree(test):
        m = getattr(comp, "report_phase", None)
        if m is not None:
            m(phase)

    # global checker summary
    summary = pyuvm.get_checker_summary()
    print(f"[CHECKER] total={summary['total']} passed={summary['passed']} failed={summary['failed']}")


def run_test(test: pyuvm.UVMTest, sim: Simulator, max_cycles: int = 1000):
    pyuvm.clear_checkers()
    pyuvm.UVMConfigDB.clear()
    asyncio.run(run_test_async(test, sim, max_cycles))
