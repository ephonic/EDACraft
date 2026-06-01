"""Skeleton implementation steps for C910-class CPU."""
from rtlgen import arch_skel

IFU_STEPS = [
    "1. Implement PCGen: PC+8, branch redirect, L0 BTB fast path",
    "2. Implement BHT: gshare predictor (4096-entry PHT, history register)",
    "3. Implement BTB: 1024-entry, 4-way, tag + target + valid",
    "4. Implement RAS: 8-entry return address stack",
    "5. Implement I-cache interface: line buffer, refill FSM",
    "6. Implement instruction buffer: 8-entry fetch buffer",
]

IDU_STEPS = [
    "1. Implement decoder: 4-wide opcode/funct/imm extraction",
    "2. Implement rename: arch→phys mapping table, free list",
    "3. Implement AIQ0: ALU issue queue 0 (32-entry wakeup-select)",
    "4. Implement AIQ1: ALU issue queue 1",
    "5. Implement BIQ: Branch issue queue",
    "6. Implement LSIQ: Load/store issue queue",
]

IU_STEPS = [
    "1. Implement ALU×2: ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU",
    "2. Implement BJU: branch resolution + target calculation",
    "3. Implement MULT: 65×65 3-stage pipelined multiplier",
    "4. Implement DIV: radix-16 SRT divider",
]

LSU_STEPS = [
    "1. Implement load queue (16 entries)",
    "2. Implement store queue (16 entries)",
    "3. Implement D-cache tag/data arrays",
    "4. Implement store-to-load forwarding",
    "5. Implement write merge buffer",
]

RTU_STEPS = [
    "1. Implement ROB: 128-entry, 4-wide allocate/retire",
    "2. Implement physical register status (pst_preg)",
    "3. Implement retire logic: 4-wide inorder commit",
]


def register_cpu_steps(template_steps: dict):
    template_steps["ifu"] = IFU_STEPS
    template_steps["idu"] = IDU_STEPS
    template_steps["iu_alu"] = IU_STEPS
    template_steps["lsu"] = LSU_STEPS
    template_steps["rtu"] = RTU_STEPS
