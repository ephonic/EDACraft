"""L2 CycleIR model for the EarphoneRV32 core.

Cycle-accurate reference model of the 3-stage RV32IM pipeline (IF → ID/EX → WB).
"""

from __future__ import annotations

from typing import Any, Callable, Dict

from rtlgen import CycleContext

from earphone.modules.common.utils import _to_u32, _to_s32, _sign_extend
from earphone.modules.rv32.layer_L1_behavior.src.behavior import (
    OPCODE_LOAD,
    OPCODE_STORE,
    OPCODE_IMM,
    OPCODE_REG,
    OPCODE_LUI,
    OPCODE_AUIPC,
    OPCODE_BRANCH,
    OPCODE_JAL,
    OPCODE_JALR,
    FUNCT3_ADDI,
    FUNCT3_SLTI,
    FUNCT3_XORI,
    FUNCT3_ORI,
    FUNCT3_ANDI,
    FUNCT3_SLLI,
    FUNCT3_SRXI,
    FUNCT3_ADD,
    FUNCT3_SUB,
    FUNCT3_SLL,
    FUNCT3_SLT,
    FUNCT3_XOR,
    FUNCT3_SRL,
    FUNCT3_SRA,
    FUNCT3_OR,
    FUNCT3_AND,
    FUNCT3_BEQ,
    FUNCT3_BNE,
    FUNCT3_BLT,
    FUNCT3_BGE,
    FUNCT3_BLTU,
    FUNCT3_BGEU,
    FUNCT3_LB,
    FUNCT3_LH,
    FUNCT3_LW,
    FUNCT3_LBU,
    FUNCT3_LHU,
    FUNCT7_DEFAULT,
    FUNCT7_SUB,
    FUNCT7_MULDIV,
)


def rv32im_cycle_model() -> Callable[[CycleContext], None]:
    """Cycle-level model of the 3-stage RV32IM pipeline."""

    def behavior(ctx: CycleContext):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['pc'] = 0x1000
            ctx.state['fetch_valid'] = 0
            ctx.state['exec_valid'] = 0
            ctx.state['wb_valid'] = 0
            ctx.state['rf'] = [0] * 32
            return

        pc = ctx.state.get('pc', 0x1000)
        fetch_valid = ctx.state.get('fetch_valid', 0)
        exec_valid = ctx.state.get('exec_valid', 0)
        wb_valid = ctx.state.get('wb_valid', 0)
        rf = ctx.state.get('rf', [0] * 32)
        rf[0] = 0

        exec_instr = ctx.state.get('exec_instr', 0)
        exec_pc = ctx.state.get('exec_pc', 0)
        wb_rd = ctx.state.get('wb_rd', 0)
        wb_result = ctx.state.get('wb_result', 0)
        wb_wb_en = ctx.state.get('wb_wb_en', 0)

        # Memory interfaces are single-cycle ideal in this model
        icache_valid = ctx.get_input('icache_valid', 0)
        icache_rdata = ctx.get_input('icache_rdata', 0)
        dcache_valid = ctx.get_input('dcache_valid', 1)

        # Decode execute-stage instruction
        def decode_exec(instr, epc):
            opcode = instr & 0x7F
            rd = (instr >> 7) & 0x1F
            funct3 = (instr >> 12) & 0x7
            rs1 = (instr >> 15) & 0x1F
            rs2 = (instr >> 20) & 0x1F
            funct7 = (instr >> 25) & 0x7F
            imm_i = _sign_extend(instr >> 20, 12)
            imm_s = _sign_extend(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12)
            imm_b = _sign_extend(((instr >> 31) << 12) | ((instr & 0x80) << 5) |
                                 ((instr >> 20) & 0x7E0) | ((instr >> 7) & 0x1E), 13)
            imm_u = instr & 0xFFFFF000
            imm_j = _sign_extend(((instr >> 31) << 20) | ((instr >> 20) & 0xFF800) |
                                 ((instr >> 9) & 0x7FE) | ((instr >> 21) & 0x100000), 21)
            v1 = rf[rs1]
            v2 = rf[rs2]

            is_rtype = (opcode == OPCODE_REG)
            is_itype = (opcode == OPCODE_IMM)
            is_load = (opcode == OPCODE_LOAD)
            is_store = (opcode == OPCODE_STORE)

            result = 0
            branch_taken = False
            branch_target = epc + 4
            mem_addr = 0
            mem_write = False

            if is_itype:
                if funct3 == FUNCT3_ADDI:
                    result = _to_u32(v1 + imm_i)
                elif funct3 == FUNCT3_SLTI:
                    result = 1 if _to_s32(v1) < _to_s32(imm_i) else 0
                elif funct3 == FUNCT3_XORI:
                    result = _to_u32(v1 ^ imm_i)
                elif funct3 == FUNCT3_ORI:
                    result = _to_u32(v1 | imm_i)
                elif funct3 == FUNCT3_ANDI:
                    result = _to_u32(v1 & imm_i)
                elif funct3 == FUNCT3_SLLI:
                    shamt = (instr >> 20) & 0x1F
                    result = _to_u32(v1 << shamt)
                elif funct3 == FUNCT3_SRXI:
                    shamt = (instr >> 20) & 0x1F
                    result = _to_u32(_to_s32(v1) >> shamt) if (instr >> 30) & 1 else v1 >> shamt
                wb_en = 1
            elif is_rtype:
                if funct7 == FUNCT7_MULDIV:
                    # M extension — single-cycle model
                    if funct3 == 0b000:
                        result = _to_u32(_to_s32(v1) * _to_s32(v2))
                    elif funct3 == 0b001:
                        result = _to_u32(((_to_s32(v1) * _to_s32(v2)) >> 32) & 0xFFFFFFFF)
                    elif funct3 == 0b011:
                        result = _to_u32(((v1 & 0xFFFFFFFF) * (v2 & 0xFFFFFFFF) >> 32) & 0xFFFFFFFF)
                    elif funct3 == 0b100:
                        result = 0xFFFFFFFF if v2 == 0 else _to_u32(int(_to_s32(v1) / _to_s32(v2)))
                    elif funct3 == 0b101:
                        result = 0xFFFFFFFF if v2 == 0 else (v1 & 0xFFFFFFFF) // (v2 & 0xFFFFFFFF)
                    elif funct3 == 0b110:
                        result = v1 if v2 == 0 else _to_u32(_to_s32(v1) % _to_s32(v2))
                    elif funct3 == 0b111:
                        result = v1 if v2 == 0 else (v1 & 0xFFFFFFFF) % (v2 & 0xFFFFFFFF)
                    else:
                        result = _to_u32(((_to_s32(v1) * (v2 & 0xFFFFFFFF)) >> 32) & 0xFFFFFFFF)
                else:
                    if funct3 == FUNCT3_ADD:
                        result = _to_u32(v1 - v2) if funct7 == FUNCT7_SUB else _to_u32(v1 + v2)
                    elif funct3 == FUNCT3_SLL:
                        result = _to_u32(v1 << (v2 & 0x1F))
                    elif funct3 == FUNCT3_SLT:
                        result = 1 if _to_s32(v1) < _to_s32(v2) else 0
                    elif funct3 == FUNCT3_XOR:
                        result = _to_u32(v1 ^ v2)
                    elif funct3 == FUNCT3_SRL:
                        result = _to_u32(_to_s32(v1) >> (v2 & 0x1F)) if (instr >> 30) & 1 else v1 >> (v2 & 0x1F)
                    elif funct3 == FUNCT3_OR:
                        result = _to_u32(v1 | v2)
                    elif funct3 == FUNCT3_AND:
                        result = _to_u32(v1 & v2)
                wb_en = 1
            elif is_load:
                mem_addr = _to_u32(v1 + imm_i)
                result = 0
                wb_en = 1
            elif is_store:
                mem_addr = _to_u32(v1 + imm_s)
                result = 0
                wb_en = 0
                mem_write = True
            elif opcode == OPCODE_LUI:
                result = imm_u
                wb_en = 1
            elif opcode == OPCODE_AUIPC:
                result = _to_u32(epc + imm_u)
                wb_en = 1
            elif opcode == OPCODE_JAL:
                result = _to_u32(epc + 4)
                branch_taken = True
                branch_target = _to_u32(epc + imm_j)
                wb_en = 1
            elif opcode == OPCODE_JALR:
                result = _to_u32(epc + 4)
                branch_taken = True
                branch_target = _to_u32(v1 + imm_i) & 0xFFFFFFFE
                wb_en = 1
            elif opcode == OPCODE_BRANCH:
                taken = False
                if funct3 == FUNCT3_BEQ:
                    taken = (v1 == v2)
                elif funct3 == FUNCT3_BNE:
                    taken = (v1 != v2)
                elif funct3 == FUNCT3_BLT:
                    taken = (_to_s32(v1) < _to_s32(v2))
                elif funct3 == FUNCT3_BGE:
                    taken = (_to_s32(v1) >= _to_s32(v2))
                elif funct3 == FUNCT3_BLTU:
                    taken = ((v1 & 0xFFFFFFFF) < (v2 & 0xFFFFFFFF))
                elif funct3 == FUNCT3_BGEU:
                    taken = ((v1 & 0xFFFFFFFF) >= (v2 & 0xFFFFFFFF))
                branch_taken = taken
                branch_target = _to_u32(epc + imm_b)
                wb_en = 0
            else:
                wb_en = 0

            return {
                'rd': rd, 'wb_en': wb_en, 'result': result,
                'branch_taken': branch_taken, 'branch_target': branch_target,
                'mem_addr': mem_addr, 'mem_write': mem_write, 'mem_wdata': v2,
            }

        # Decode current execute instruction
        dec = decode_exec(exec_instr, exec_pc)

        # Handle load data (single-cycle in model)
        load_result = dec['result']
        if (exec_valid and (exec_instr & 0x7F) == OPCODE_LOAD and dcache_valid):
            addr = dec['mem_addr']
            funct3 = (exec_instr >> 12) & 0x7
            if funct3 == FUNCT3_LB:
                load_result = _sign_extend(ctx.get_input('mem_byte', ctx.state.get('mem', {}).get(addr, 0)), 8)
            elif funct3 == FUNCT3_LH:
                lb = ctx.state.get('mem', {}).get(addr, 0)
                lh = ctx.state.get('mem', {}).get(addr + 1, 0)
                load_result = _sign_extend((lh << 8) | lb, 16)
            elif funct3 == FUNCT3_LW:
                m = ctx.state.get('mem', {})
                load_result = _to_s32((m.get(addr + 3, 0) << 24) | (m.get(addr + 2, 0) << 16) |
                                      (m.get(addr + 1, 0) << 8) | m.get(addr, 0))
            elif funct3 == FUNCT3_LBU:
                load_result = ctx.state.get('mem', {}).get(addr, 0) & 0xFF
            elif funct3 == FUNCT3_LHU:
                m = ctx.state.get('mem', {})
                load_result = ((m.get(addr + 1, 0) << 8) | m.get(addr, 0)) & 0xFFFF

        # Writeback to register file
        if wb_valid and wb_wb_en and wb_rd != 0:
            rf[wb_rd] = wb_result & 0xFFFFFFFF
        rf[0] = 0

        # Update pipeline
        fetch_instr = ctx.state.get('fetch_instr', 0)
        new_fetch_valid = 0
        new_exec_valid = 0
        new_wb_valid = 0
        new_pc = pc

        if dec['branch_taken'] and exec_valid:
            new_pc = dec['branch_target']
            # Flush fetch/exec
            new_fetch_valid = 0
            new_exec_valid = 0
        else:
            # Fetch advances when instruction available
            if icache_valid:
                new_fetch_valid = 1
                fetch_instr = icache_rdata & 0xFFFFFFFF
            else:
                new_fetch_valid = 0
            new_pc = _to_u32(pc + 4)
            new_exec_valid = fetch_valid
            new_wb_valid = exec_valid

        ctx.state['pc'] = new_pc
        ctx.state['fetch_valid'] = new_fetch_valid
        ctx.state['fetch_instr'] = fetch_instr
        ctx.state['exec_valid'] = new_exec_valid
        ctx.state['exec_instr'] = fetch_instr
        ctx.state['exec_pc'] = pc
        ctx.state['wb_valid'] = new_wb_valid
        ctx.state['wb_rd'] = dec['rd']
        ctx.state['wb_wb_en'] = dec['wb_en']
        ctx.state['wb_result'] = load_result
        ctx.state['rf'] = rf

        # Memory outputs
        ctx.set_output('icache_req', 1)
        ctx.set_output('icache_addr', pc)
        ctx.set_output('dcache_req', 1 if (exec_valid and ((exec_instr & 0x7F) in (OPCODE_LOAD, OPCODE_STORE))) else 0)
        ctx.set_output('dcache_addr', dec['mem_addr'])
        ctx.set_output('dcache_wdata', dec['mem_wdata'])
        ctx.set_output('dcache_wen', 1 if dec['mem_write'] else 0)
        ctx.set_output('retire_valid', 1 if (new_wb_valid and dec['wb_en']) else 0)
        ctx.set_output('retire_rd', dec['rd'])
        ctx.set_output('retire_result', load_result)

    return behavior


def describe() -> Dict[str, Any]:
    return {
        "name": "EarphoneRV32",
        "layer": "L2_cycle",
        "status": "implemented",
        "description": "Cycle-accurate 3-stage RV32IM pipeline model (IF → ID/EX → WB).",
        "pipeline_stages": ["IF", "ID/EX", "WB"],
        "mul_latency_cycles": 1,
        "div_latency_cycles": "32 (iterative)",
    }
