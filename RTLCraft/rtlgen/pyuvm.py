"""
rtlgen.pyuvm — 原生 Python UVM 框架 DSL

提供与 UVM 1.1d 结构对应的 Python 类，支持 component 树构建、
TLM 端口连接、sequence/transaction 定义。编写完成后可通过
rtlgen.pyuvmgen 一键转译为原生 SystemVerilog/UVM。
"""
from __future__ import annotations

import asyncio
import random
import re
from typing import Any, Callable, Dict, List, Optional, Type

_current_scheduler = None
_current_sequence = None

_checkers: List[Dict[str, Any]] = []


def assert_eq(actual: Any, expected: Any, msg: str = ""):
    ok = actual == expected
    _checkers.append({"type": "assert_eq", "ok": ok, "msg": msg or f"assert_eq {actual} == {expected}"})
    if not ok:
        uvm_error("CHECKER", f"{msg}: expected {expected}, got {actual}")
    return ok


def get_checker_summary() -> Dict[str, int]:
    total = len(_checkers)
    passed = sum(1 for c in _checkers if c["ok"])
    return {"total": total, "passed": passed, "failed": total - passed}


def clear_checkers():
    _checkers.clear()


class Coverage:
    """轻量级功能覆盖率容器。"""

    def __init__(self, name: str = ""):
        self.name = name
        self.hits: Dict[Any, int] = {}
        self.total_bins: int = 0

    def define_bins(self, bins: List[Any]):
        """预定义覆盖点。"""
        for b in bins:
            if b not in self.hits:
                self.hits[b] = 0
        self.total_bins = len(self.hits)

    def sample(self, value: Any):
        self.hits[value] = self.hits.get(value, 0) + 1

    def get_coverage(self) -> float:
        if self.total_bins == 0:
            return 0.0
        covered = sum(1 for v in self.hits.values() if v > 0)
        return covered / self.total_bins * 100.0

    def report(self):
        print(f"[COVERAGE] {self.name}: {self.get_coverage():.2f}% ({sum(1 for v in self.hits.values() if v > 0)}/{self.total_bins})")


# -----------------------------------------------------------------
# UVM 宏 / 辅助函数（Python 侧占位，生成 SV 时映射为对应语句）
# -----------------------------------------------------------------
class UVMFatalError(RuntimeError):
    pass


def uvm_fatal(id: str, msg: str):
    raise UVMFatalError(f"UVM_FATAL [{id}] {msg}")


def uvm_error(id: str, msg: str):
    print(f"[UVM_ERROR] [{id}] {msg}")


def uvm_warning(id: str, msg: str):
    print(f"[UVM_WARNING] [{id}] {msg}")


def uvm_info(id: str, msg: str, verbosity: int = 0):
    print(f"[UVM_INFO] [{id}] {msg}")


def repeat(n: int):
    """在 Python 侧返回 range(n)，生成 SV 时映射为 repeat (n) begin ... end。"""
    return range(n)


async def delay(cycles: int = 1):
    """在 Python 侧挂起指定周期，生成 SV 时转为 @(posedge clk)。"""
    s = _current_scheduler
    if s is not None:
        await s.wait_cycles(cycles)


def create(cls: Type[Any], name: str) -> Any:
    """模拟 UVM `type_id::create(name)`。"""
    return cls(name)


async def start_item(item: Any):
    seq = _current_sequence
    if seq is not None and seq.sequencer is not None:
        await seq.sequencer._fifo.put(item)


async def finish_item(item: Any):
    seq = _current_sequence
    if seq is not None and seq.sequencer is not None:
        await seq.sequencer._item_done_event.wait()
        seq.sequencer._item_done_event.clear()


async def uvm_do(item: Any):
    """UVM `uvm_do` 的 Python 等价物：start_item + randomize + finish_item。"""
    await start_item(item)
    if not randomize(item):
        uvm_fatal("SEQ", "Randomize failed")
    await finish_item(item)


def _parse_sv_constraint(value: str) -> Optional[int]:
    """Parse simple SV-style 'inside {[low:high]}' constraint and return a random int."""
    import random
    m = re.match(r"inside\s*\{\[(\d+):(\d+)\]\}", value.strip())
    if m:
        low, high = int(m.group(1)), int(m.group(2))
        return random.randint(low, high)
    return None


async def uvm_do_with(item: Any, constraints: Optional[Any] = None):
    """UVM `uvm_do_with` 的 Python 等价物：start_item + 约束随机化 + finish_item。
    constraints 可以是 dict（字段->固定值、lambda、或 SV-style 'inside {[low:high]}' 字符串）、
    callable（对 item 做后处理）或 None。
    """
    await start_item(item)
    if constraints is not None:
        if isinstance(constraints, dict):
            # 先随机化，再强制覆盖约束字段（硬约束）
            if not randomize(item):
                uvm_fatal("SEQ", "Randomize failed")
            for k, v in constraints.items():
                if callable(v):
                    setattr(item, k, v(item))
                elif isinstance(v, str):
                    parsed = _parse_sv_constraint(v)
                    if parsed is not None:
                        setattr(item, k, parsed)
                    else:
                        setattr(item, k, v)
                else:
                    setattr(item, k, v)
        elif callable(constraints):
            if not randomize(item):
                uvm_fatal("SEQ", "Randomize failed")
            constraints(item)
        else:
            uvm_fatal("SEQ", f"Unsupported constraints type: {type(constraints)}")
    else:
        if not randomize(item):
            uvm_fatal("SEQ", "Randomize failed")
    await finish_item(item)


def randomize(item: Any) -> bool:
    """Python 侧调用 item.randomize()（如果存在），否则返回 True。生成 SV 时转为 item.randomize()。"""
    if hasattr(item, "randomize") and callable(item.randomize):
        return item.randomize()
    return True


# -----------------------------------------------------------------
# Phase
# -----------------------------------------------------------------
class UVMPhase:
    """UVM phase 占位类。"""

    def raise_objection(self, obj: Any):
        pass

    def drop_objection(self, obj: Any):
        pass


# -----------------------------------------------------------------
# TLM Ports
# -----------------------------------------------------------------
class _TLMPortBase:
    def __init__(self, name: str = ""):
        self.name = name
        self._connected_to = None
        self._queue: Optional[asyncio.Queue] = None

    def _bind_queue(self, queue: asyncio.Queue):
        self._queue = queue


class UVMBlockingPutPort(_TLMPortBase):
    async def put(self, txn: Any):
        if self._queue is not None:
            await self._queue.put(txn)


class UVMNonBlockingPutPort(_TLMPortBase):
    def try_put(self, txn: Any) -> bool:
        if self._queue is not None and self._queue.qsize() < 16:
            try:
                self._queue.put_nowait(txn)
                return True
            except asyncio.QueueFull:
                pass
        return False


class UVMBlockingGetPort(_TLMPortBase):
    async def get(self) -> Any:
        if self._queue is not None:
            return await self._queue.get()
        return None


class UVMNonBlockingGetPort(_TLMPortBase):
    def try_get(self) -> Any:
        if self._queue is not None and not self._queue.empty():
            try:
                return self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        return None


class UVMBlockingPeekPort(_TLMPortBase):
    async def peek(self) -> Any:
        if self._queue is not None:
            item = await self._queue.get()
            await self._queue.put(item)
            return item
        return None


class UVMNonBlockingPeekPort(_TLMPortBase):
    def try_peek(self) -> Any:
        if self._queue is not None and not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                self._queue.put_nowait(item)
                return item
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass
        return None


class UVMSeqItemPort:
    """Driver 侧的 seq_item_port。"""

    def __init__(self):
        self._connected_to = None
        self._queue: Optional[asyncio.Queue] = None
        self._item_done_event: Optional[asyncio.Event] = None

    async def get_next_item(self, item_var: Any = None):
        if self._queue is not None:
            return await self._queue.get()
        return None

    def item_done(self):
        if self._item_done_event is not None:
            self._item_done_event.set()

    def connect(self, exp):
        self._connected_to = exp
        if hasattr(exp, "_fifo"):
            self._queue = exp._fifo
        if hasattr(exp, "_item_done_event"):
            self._item_done_event = exp._item_done_event


class UVMSeqItemExport:
    """Sequencer 侧的 seq_item_export。"""
    pass


class UVMAnalysisPort:
    """Monitor -> Scoreboard 的分析端口（支持多播）。"""

    def __init__(self):
        self._connected_to: List[Any] = []

    def write(self, txn: Any):
        for target in self._connected_to:
            if hasattr(target, "write"):
                target.write(txn)
            else:
                parent = getattr(target, "parent", None)
                m = getattr(parent, "write", None) if parent is not None else None
                if m is not None:
                    m(txn)

    def connect(self, imp):
        self._connected_to.append(imp)


class UVMAnalysisImp:
    """Scoreboard 侧的分析导入端口。"""

    def __init__(self, name: str, parent: "UVMComponent"):
        self.name = name
        self.parent = parent

    def write(self, txn: Any):
        parent = getattr(self, "parent", None)
        m = getattr(parent, "write", None) if parent is not None else None
        if m is not None:
            m(txn)


class UVMAnalysisFIFO:
    """带缓冲的 analysis port，支持 monitor 写入、scoreboard 读取。"""

    def __init__(self, name: str = "", maxsize: int = 0):
        self.name = name
        self._queue = asyncio.Queue(maxsize=maxsize)

    def write(self, txn: Any):
        try:
            self._queue.put_nowait(txn)
        except asyncio.QueueFull:
            pass

    async def get(self) -> Any:
        return await self._queue.get()

    def try_get(self) -> Any:
        if not self._queue.empty():
            try:
                return self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        return None

    async def peek(self) -> Any:
        item = await self._queue.get()
        await self._queue.put(item)
        return item

    def try_peek(self) -> Any:
        if not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                self._queue.put_nowait(item)
                return item
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass
        return None

    def connect_export(self, port: UVMAnalysisPort):
        """让 monitor 的 analysis_port 连到本 FIFO。"""
        port.connect(self)

    def connect_get_port(self, port: _TLMPortBase):
        """让 get_port 绑定到本 FIFO 的队列。"""
        port._bind_queue(self._queue)


# -----------------------------------------------------------------
# Component Base
# -----------------------------------------------------------------
class UVMConfigDB:
    """轻量级 UVM config_db 实现，支持类型化存储与层级路径通配符匹配。"""

    _global_db: Dict[str, List[Tuple[str, str, Any, Optional[Type]]]] = {}

    @classmethod
    def set(cls, cntxt: Optional[Any], inst_name: str, field_name: str, value: Any, val_type: Optional[Type] = None):
        key = f"{field_name}"
        entry = (inst_name, cls._full_name(cntxt), value, val_type)
        cls._global_db.setdefault(key, []).append(entry)

    @classmethod
    def get(cls, cntxt: Optional[Any], inst_name: str, field_name: str, val_type: Optional[Type] = None) -> Any:
        key = f"{field_name}"
        entries = cls._global_db.get(key, [])
        target_path = cls._full_name(cntxt)
        # 从最新到最旧匹配
        for e_inst, e_path, e_val, e_type in reversed(entries):
            if val_type is not None and e_type is not None and not issubclass(e_type, val_type):
                continue
            if cls._match(inst_name, target_path, e_inst, e_path):
                return e_val
        return None

    @classmethod
    def clear(cls):
        cls._global_db.clear()

    @staticmethod
    def _full_name(cntxt: Optional[Any]) -> str:
        if cntxt is None:
            return ""
        if hasattr(cntxt, "get_full_name"):
            return cntxt.get_full_name()
        return str(cntxt)

    @staticmethod
    def _match(req_inst: str, req_path: str, db_inst: str, db_path: str) -> bool:
        # 简化匹配：路径前缀匹配 + inst_name 通配符
        path_ok = db_path == "" or req_path.startswith(db_path) or db_path == "*"
        if not path_ok:
            return False
        if db_inst == "*":
            return True
        return req_inst == db_inst or (db_inst.endswith("*") and req_inst.startswith(db_inst[:-1]))


class UVMComponent:
    """UVM component 基类。"""

    def __init__(self, name: str, parent: Optional["UVMComponent"] = None):
        self.name = name
        self.parent = parent
        self.children: List[UVMComponent] = []
        self._cfg_db: Dict[str, Any] = {}
        self._tlm_connections: List[Tuple[str, str, Any]] = []  # (src_path, port_name, target_path/imp)
        if parent is not None:
            parent.children.append(self)

    def build_phase(self, phase: UVMPhase):
        pass

    def connect_phase(self, phase: UVMPhase):
        pass

    def run_phase(self, phase: UVMPhase):
        pass

    def end_of_elaboration_phase(self, phase: UVMPhase):
        pass

    def report_phase(self, phase: UVMPhase):
        pass

    # 旧的简单 API（保留兼容）
    def cfg_db_set(self, key: str, value: Any):
        self._cfg_db[key] = value

    def cfg_db_get(self, key: str) -> Any:
        if key in self._cfg_db:
            return self._cfg_db[key]
        if self.parent is not None:
            return self.parent.cfg_db_get(key)
        return None

    # 新的 UVM 风格 API
    def uvm_config_db_set(self, field_name: str, value: Any, val_type: Optional[Type] = None):
        UVMConfigDB.set(self, self.name, field_name, value, val_type)

    def uvm_config_db_get(self, field_name: str, val_type: Optional[Type] = None) -> Any:
        v = UVMConfigDB.get(self, self.name, field_name, val_type)
        if v is None:
            v = self.cfg_db_get(field_name)
        return v

    def get_full_name(self) -> str:
        if self.parent is None or self.parent.name == "":
            return self.name
        return f"{self.parent.get_full_name()}.{self.name}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"


# -----------------------------------------------------------------
# Field / Transaction
# -----------------------------------------------------------------
class UVMField:
    def __init__(self, name: str, width: int = 1, access: str = "UVM_ALL_ON"):
        self.name = name
        self.width = width
        self.access = access


class UVMSequenceItem(UVMComponent):
    """UVM sequence_item。"""

    _fields: List[Any] = []

    def __init__(self, name: str = ""):
        super().__init__(name or self.__class__.__name__)
        # 规范化 fields（支持 tuple 和 UVMField 混合）
        normalized = []
        for f in self._fields:
            if isinstance(f, tuple):
                normalized.append(UVMField(f[0], f[1] if len(f) > 1 else 1, f[2] if len(f) > 2 else "UVM_ALL_ON"))
            else:
                normalized.append(f)
        self._fields = normalized
        # 为每个 field 创建实例属性（便于 Python 侧访问）
        for f in self._fields:
            setattr(self, f.name, 0)

    def randomize(self) -> bool:
        """基于 Python random 模块对每个 field 做随机化。"""
        for f in self._fields:
            if f.width == 1:
                setattr(self, f.name, random.getrandbits(1))
            else:
                setattr(self, f.name, random.getrandbits(f.width))
        return True


# -----------------------------------------------------------------
# Sequence / Sequencer
# -----------------------------------------------------------------
class UVMSequence(UVMComponent):
    """UVM sequence。支持嵌套 sequence 启动（virtual sequence）。"""

    num_transactions: int = 10

    def __init__(self, name: str = "", parent: Optional[UVMComponent] = None, txn_type: Optional[Type[UVMSequenceItem]] = None):
        super().__init__(name or self.__class__.__name__, parent)
        self.sequencer: Optional["UVMSequencer"] = None
        self.p_sequencer: Optional["UVMSequencer"] = None
        self.starting_phase: Optional[UVMPhase] = None
        if txn_type is not None:
            self._txn_type_name = txn_type.__name__
            if not hasattr(self.__class__, "_txn_type_name"):
                self.__class__._txn_type_name = txn_type.__name__

    def pre_body(self):
        pass

    def body(self):
        pass

    def post_body(self):
        pass

    def kill(self):
        """终止当前 sequence 及其所有子 sequence。"""
        self._cancelled = True
        for child in list(self.children):
            if isinstance(child, UVMSequence):
                child.kill()

    def is_relevant(self) -> bool:
        """返回 sequence 是否仍在活跃状态（未被 kill）。"""
        return not getattr(self, "_cancelled", False)

    async def wait_for_grant(self, sequencer: Optional["UVMSequencer"] = None):
        """等待 sequencer 授权（在 Python 侧模拟为 next_item 可用时返回）。"""
        sqr = sequencer or self.sequencer
        if sqr is not None:
            while sqr._fifo.empty():
                await asyncio.sleep(0)
        else:
            await asyncio.sleep(0)

    def _check_cancelled(self):
        if getattr(self, "_cancelled", False):
            raise asyncio.CancelledError("Sequence killed")

    async def start(self, sequencer: "UVMSequencer", parent_sequence: Optional["UVMSequence"] = None, starting_phase: Optional[UVMPhase] = None):
        self.sequencer = sequencer
        self.p_sequencer = sequencer
        self._cancelled = False
        if starting_phase is not None:
            self.starting_phase = starting_phase
        elif parent_sequence is not None:
            self.starting_phase = parent_sequence.starting_phase

        global _current_sequence
        prev = _current_sequence
        _current_sequence = self
        try:
            self._check_cancelled()
            self.pre_body()
            self._check_cancelled()
            await self.body()
            self._check_cancelled()
            self.post_body()
        finally:
            _current_sequence = prev


class UVMVirtualSequence(UVMSequence):
    """Virtual sequence：不直接发送 item，而是启动子 sequence。"""
    pass


class UVMSequencer(UVMComponent):
    """UVM sequencer。"""

    def __init__(self, name: str, parent: Optional[UVMComponent] = None, txn_type: Optional[Type[UVMSequenceItem]] = None):
        super().__init__(name, parent)
        self.seq_item_export = UVMSeqItemExport()
        self._fifo = asyncio.Queue()
        self._item_done_event = asyncio.Event()
        self.seq_item_export._fifo = self._fifo
        self.seq_item_export._item_done_event = self._item_done_event
        if txn_type is not None:
            self._txn_type_name = txn_type.__name__
            if not hasattr(self.__class__, "_txn_type_name"):
                self.__class__._txn_type_name = txn_type.__name__


# -----------------------------------------------------------------
# Driver / Monitor / Agent / Scoreboard / Env / Test
# -----------------------------------------------------------------
class UVMDriver(UVMComponent):
    """UVM driver。"""

    def __init__(
        self,
        name: str,
        parent: Optional[UVMComponent] = None,
        txn_type: Optional[Type[UVMSequenceItem]] = None,
    ):
        super().__init__(name, parent)
        self.seq_item_port = UVMSeqItemPort()
        self.txn_type = txn_type
        if txn_type is not None:
            self._txn_type_name = txn_type.__name__
            if not hasattr(self.__class__, "_txn_type_name"):
                self.__class__._txn_type_name = txn_type.__name__
        self.req: Optional[Any] = None
        self.rsp: Optional[Any] = None
        self.vif: Optional[Any] = None

    def get_req_type_name(self) -> str:
        return getattr(self, "_txn_type_name", "uvm_sequence_item")

    def get_rsp_type_name(self) -> str:
        return getattr(self, "_txn_type_name", "uvm_sequence_item")


class UVMMonitor(UVMComponent):
    """UVM monitor。"""

    def __init__(self, name: str, parent: Optional[UVMComponent] = None):
        super().__init__(name, parent)
        self.ap = UVMAnalysisPort()
        self.vif: Optional[Any] = None


class UVMAgent(UVMComponent):
    """UVM agent。"""

    def __init__(
        self,
        name: str,
        parent: Optional[UVMComponent] = None,
        is_active: bool = True,
    ):
        super().__init__(name, parent)
        self.is_active = is_active
        self.sqr: Optional[UVMSequencer] = None
        self.drv: Optional[UVMDriver] = None
        self.mon: Optional[UVMMonitor] = None


class UVMScoreboard(UVMComponent):
    """UVM scoreboard。"""

    def __init__(self, name: str, parent: Optional[UVMComponent] = None, txn_type: Optional[Type[UVMSequenceItem]] = None):
        super().__init__(name, parent)
        self.exp = UVMAnalysisImp("exp", self)
        if txn_type is not None:
            self._txn_type_name = txn_type.__name__
            if not hasattr(self.__class__, "_txn_type_name"):
                self.__class__._txn_type_name = txn_type.__name__
        self.expect_queue: List[Any] = []
        self.actual_queue: List[Any] = []

    def get_txn_type_name(self) -> str:
        return getattr(self, "_txn_type_name", "uvm_sequence_item")


class UVMEnv(UVMComponent):
    """UVM env。"""
    pass


class UVMTest(UVMComponent):
    """UVM test。"""
    pass


# -----------------------------------------------------------------
# Register Abstraction Layer (RAL) — 基础框架
# -----------------------------------------------------------------
class UVMRegField:
    """寄存器字段。"""

    def __init__(self, name: str, width: int = 1, lsb_pos: int = 0, access: str = "RW", reset: int = 0):
        self.name = name
        self.width = width
        self.lsb_pos = lsb_pos
        self.access = access  # "RW", "RO", "WO", "RW1C", "RW1S" ...
        self.reset = reset
        self.value = reset

    def read(self) -> int:
        return (self.value >> self.lsb_pos) & ((1 << self.width) - 1)

    def write(self, val: int):
        mask = ((1 << self.width) - 1) << self.lsb_pos
        self.value = (self.value & ~mask) | ((int(val) << self.lsb_pos) & mask)


class UVMReg:
    """寄存器。"""

    def __init__(self, name: str, width: int = 32, reset: int = 0):
        self.name = name
        self.width = width
        self.reset = reset
        self.value = reset
        self.fields: Dict[str, UVMRegField] = {}

    def add_field(self, field: UVMRegField):
        self.fields[field.name] = field
        # 将字段 reset 合并到寄存器 reset
        mask = ((1 << field.width) - 1) << field.lsb_pos
        self.reset = (self.reset & ~mask) | ((field.reset << field.lsb_pos) & mask)
        self.value = self.reset

    def read(self) -> int:
        # 从各字段重新组装值，保证一致性
        val = self.value
        for f in self.fields.values():
            mask = ((1 << f.width) - 1) << f.lsb_pos
            val = (val & ~mask) | ((f.value << f.lsb_pos) & mask)
        self.value = val & ((1 << self.width) - 1)
        return self.value

    def write(self, val: int):
        self.value = int(val) & ((1 << self.width) - 1)
        for f in self.fields.values():
            f.value = self.value

    def reset_val(self):
        self.value = self.reset
        for f in self.fields.values():
            f.value = self.reset

    def mirror(self):
        """返回寄存器期望的 mirror 值（当前 Python 侧和实际值相同）。"""
        return self.read()


class UVMRegBlock(UVMComponent):
    """寄存器块，可包含多个 UVMReg 和子 UVMRegBlock。"""

    def __init__(self, name: str, parent: Optional[UVMComponent] = None):
        super().__init__(name, parent)
        self.regs: Dict[str, UVMReg] = {}
        self.sub_blocks: Dict[str, "UVMRegBlock"] = {}
        self.map: Dict[int, UVMReg] = {}  # offset -> reg

    def add_reg(self, reg: UVMReg, offset: int):
        self.regs[reg.name] = reg
        self.map[offset] = reg

    def add_sub_block(self, block: "UVMRegBlock"):
        self.sub_blocks[block.name] = block

    def read_reg(self, offset: int) -> int:
        reg = self.map.get(offset)
        if reg is None:
            uvm_error("RAL", f"No register at offset 0x{offset:04x}")
            return 0
        return reg.read()

    def write_reg(self, offset: int, value: int):
        reg = self.map.get(offset)
        if reg is None:
            uvm_error("RAL", f"No register at offset 0x{offset:04x}")
            return
        reg.write(value)

    def reset(self):
        for reg in self.regs.values():
            reg.reset_val()
        for blk in self.sub_blocks.values():
            blk.reset()


class UVMRegPredictor(UVMComponent):
    """基于总线 transaction 的寄存器 predictor。"""

    def __init__(self, name: str, parent: Optional[UVMComponent] = None, reg_block: Optional[UVMRegBlock] = None):
        super().__init__(name, parent)
        self.reg_block = reg_block
        self.exp = UVMAnalysisImp("exp", self)

    def write(self, txn: Any):
        """接收 monitor 的 bus transaction，更新对应寄存器 mirror 值。"""
        if self.reg_block is None:
            return
        addr = getattr(txn, "addr", None)
        data = getattr(txn, "data", None)
        we = getattr(txn, "we", None)
        # 兼容非标准 txn（如 CounterTxn 的 en 字段）
        if addr is None and hasattr(txn, "en"):
            addr = 0
            data = getattr(txn, "en")
            we = 1
        if addr is None or data is None:
            return
        reg = self.reg_block.map.get(int(addr), None)
        if reg is None:
            return
        if we:
            reg.write(int(data))
        # read 时 mirror 值不变（已是最新写入值或 reset 值）


def sv_dpi(c_decl: str = ""):
    """Mark a Python function as having a DPI-C counterpart in generated SV.

    Args:
        c_decl: The exact SystemVerilog import declaration, e.g.
                'import "DPI-C" function void dpi_sha3_256(...);'
    """
    def decorator(func):
        func._sv_dpi = c_decl
        # auto-register so that the C bridge can resolve it at runtime
        try:
            from rtlgen import dpi_runtime
            dpi_runtime.register(func.__name__, func)
        except Exception:
            pass
        return func
    return decorator
