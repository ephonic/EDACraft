"""Skeleton implementation steps for 4-core OoO RISC-V processor."""
from rtlgen import arch_skel

OFO_CORE_STEPS = [
    "1. Implement 2-wide Fetch stage (PC + I-Cache interface + branch prediction)",
    "2. Implement Decode stage (2 instructions/cycle, opcode/funct/imm extraction)",
    "3. Implement Register Rename (arch→phys mapping table, free list)",
    "4. Implement Reorder Buffer (64-entry ROB, circular FIFO)",
    "5. Implement Issue Queue (wakeup + select logic, 32 entries)",
    "6. Implement Execution Units (ALU, AGU, BRU with bypass)",
    "7. Implement Load/Store Queue (in-order load/store with forwarding)",
    "8. Implement Commit logic (retire up to 2 instr/cycle, update arch state)",
    "9. Implement Branch Predictor (gshare PHT + BTB + RAS)",
    "10. Implement MESI L1 Cache controller (tag/data/state arrays + snoop)",
    "11. Verify: single-thread IPC > 1.0 for standard benchmarks",
]

L1_CACHE_STEPS = [
    "1. Implement Tag RAM (tag comparison + MESI state bits)",
    "2. Implement Data RAM (line-based storage, 64B lines)",
    "3. Implement MESI FSM: I→S→E→M transitions",
    "4. Implement snoop handling (snoop invalidation/response)",
    "5. Implement refill FSM (miss→bus request→fill→ready)",
    "6. Verify: hit rate > 90% for standard workloads",
]

COHERENCE_BUS_STEPS = [
    "1. Implement snoop address broadcast (request → all cores)",
    "2. Implement snoop response collection (ack/nack from each core)",
    "3. Implement MESI state transition on bus (shared/exclusive responses)",
    "4. Implement writeback handling (dirty data transfer between caches)",
    "5. Verify: MESI protocol correctness (no data races)",
]

NOC_ROUTER_STEPS = [
    "1. Implement input FIFO buffers (4-deep per port)",
    "2. Implement XY routing logic",
    "3. Implement 5x5 crossbar switch",
    "4. Implement priority arbitration",
    "5. Verify: 1 flit/cycle throughput per port",
]


def register_ooo_skeleton_steps(template_steps: dict):
    template_steps["ooo_core"] = OFO_CORE_STEPS
    template_steps["l1_cache"] = L1_CACHE_STEPS
    template_steps["coherence_bus"] = COHERENCE_BUS_STEPS
    template_steps["noc_router"] = NOC_ROUTER_STEPS
