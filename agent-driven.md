# Agent-Driven Design: 三层增量改进方案

## 动机

当前 EDACode Agent + RTLCraft 之间存在断层：
- 生成失败后没有重试/回退机制，必须从头再来
- 跨 session 没有记忆，同样的错误反复犯
- Spec→Plan→Exec 三层逻辑混合，问题定位困难

**不做**大而全的重构，而是做**三个可独立交付的增量改进**。

---

## 改进一：CheckpointStore

### 目标
在每次 tool call 前后、层间转换时自动 snapshot，底层用 git + JSON，支持 revert(ckpt_id)。

### 存储结构

```
.rtlcraft/checkpoints/
├── .git/                          # 自动 init 的 git 仓库
├── ckpt_<ts>_<id>_L<layer>.json   # 快照本体
└── index.json                     # 有序索引
```

### 核心接口

```python
class CheckpointStore:
    def snapshot(layer, state, summary="") -> str
    def revert(ckpt_id) -> dict | None
    def list_checkpoints() -> list[dict]
    def diff(ckpt_a, ckpt_b) -> str
```

---

## 改进二：EpisodicMemory

### 目标
session 结束时，将关键决策 + 失败模式写入 `.rtlcraft/memory/`。下次启动时注入系统提示，避免重复踩坑。

### 存储结构

```
.rtlcraft/memory/
├── sessions/<ts>_<sid>.jsonl     # 实时追加，crash-safe
├── patterns/
│   ├── errors.json
│   └── successes.json
└── index.json
```

### 核心接口

```python
class EpisodicMemory:
    def record(type, layer, task, context, action, result, patterns=None)
    def save_session(summary)
    def format_for_prompt() -> str
    def get_error_patterns() -> list[dict]
```

---

## 改进三：Layer 契约

### 目标
- L1→L2 接口：SpecIR → ArchitectureIR
- L2→L3 接口：Plan → ToolSequence
- 每个工具调用标注来自哪一层，方便问题归因

### 核心接口

```python
class Layer(IntEnum):
    L1_SPEC = 1
    L2_PLAN = 2
    L3_EXEC = 3

@dataclass
class L1ToL2:     spec, task_description, constraints, trace_id
@dataclass
class L2ToL3:     plan, task_sequence, rollback_strategy, trace_id
@dataclass
class AnnotatedToolCall:
    layer, tool_name, args, trace_id, retry_count

class LayerTracer:
    def record(tc), get_trace(id), get_by_layer(layer), summary(id)
```

---

## 文件位置

```
RTLCraft/rtlgen/
├── contracts.py      # Layer 契约（~90 行，零依赖）
├── checkpoint.py     # CheckpointStore（~220 行）
├── memory.py         # EpisodicMemory（~230 行）
├── skill_ppa.py      # （已有）供集成
└── ...               # 其他已有模块

agent-driven.md       # 本文档（项目根目录）
```

三个模块可直接被 `skill_ppa.py` 或其他 RTLCraft 组件 import 使用。
