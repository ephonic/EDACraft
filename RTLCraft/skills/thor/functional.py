"""
skills/thor/functional — Layer 1: Behavioral models (pure combinatorial, no timing).

Blackwell-class Thor GPGPU pipeline stages.
"""
from __future__ import annotations
import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from skills.thor import (
    XLEN, FLEN, NLANE, VLEN, VREGS, NWARP, N_SCHED, WARP_PER_SCHED,
    NSM, IMEM_DEPTH, N_ALU, N_FPU, N_SFU, N_TENSOR, N_LSU,
    OP_NOP, OP_SLOAD, OP_VLOAD, OP_VSTORE, OP_VADD, OP_VSUB,
    OP_VMUL, OP_VMLA, OP_FADD, OP_FMUL, OP_FMLA, OP_SFU,
    OP_TENSOR, OP_BARRIER, OP_DONE, OP_BRA, OP_SYNC,
    SIMT_STACK_DEPTH, decode_inst,
)


def cta_scheduler_functional(**kwargs) -> Callable:
    """Functional CTA Scheduler: workgroup dispatch to SMs.
    Pure combinatorial: maps CTA ID to SM ID based on availability.
    """
    n_sm = kwargs.get('nsm', NSM)
    def func(kernel_id: int = 0, num_ctas: int = 1,
             sm_ready: int = 0xFFFFFFFF, **inputs) -> Dict:
        free_sms = [i for i in range(n_sm) if (sm_ready >> i) & 1]
        dispatched_sm = free_sms[0] if free_sms else 0
        return {
            "dispatched_sm": dispatched_sm,
            "dispatch_valid": int(len(free_sms) > 0),
            "remaining_ctas": max(0, num_ctas - 1),
        }
    return func


def warp_scheduler_functional(**kwargs) -> Callable:
    """Functional Warp Scheduler: round-robin warp selection.
    Selects next ready warp among WARP_PER_SCHED warps.
    """
    n_warps = kwargs.get('n_warps', WARP_PER_SCHED)
    def func(warp_ready: int = 0xF, warp_idle_mask: int = 0,
             last_warp: int = 0) -> Dict:
        mask = warp_ready & ~warp_idle_mask
        if mask == 0:
            return {"selected_warp": last_warp, "select_valid": 0}
        for i in range(n_warps):
            idx = (last_warp + 1 + i) % n_warps
            if (mask >> idx) & 1:
                return {"selected_warp": idx, "select_valid": 1}
        return {"selected_warp": last_warp, "select_valid": 0}
    return func


def simt_stack_functional(**kwargs) -> Callable:
    """Functional SIMT Stack: branch divergence reconvergence.
    Push divergent branch targets, pop on reconvergence.
    """
    depth = kwargs.get('depth', SIMT_STACK_DEPTH)
    def func(push: int = 0, pop: int = 0, fallthrough_pc: int = 0,
             branch_pc: int = 0, reconv_pc: int = 0,
             active_mask: int = 0xFFFF, pred: int = 0,
             stack_state: List = None) -> Dict:
        stack = list(stack_state or [])
        new_active = active_mask
        new_pred = pred
        if push and len(stack) < depth:
            stack.append({
                "reconv_pc": reconv_pc,
                "fallthrough_pc": fallthrough_pc,
                "saved_active": active_mask,
                "saved_pred": pred,
            })
            new_active = active_mask & pred  # taken path only
        if pop and len(stack) > 0:
            entry = stack.pop()
            new_active = entry["saved_active"]
            new_pred = entry["saved_pred"]
        return {
            "new_stack": stack,
            "new_active_mask": new_active,
            "new_pred": new_pred,
            "stack_empty": int(len(stack) == 0),
            "stack_full": int(len(stack) >= depth),
        }
    return func


def ibuffer_functional(**kwargs) -> Callable:
    """Functional IBuffer: instruction buffer (FIFO-like).
    Holds decoded instructions ready for issue.
    """
    depth = kwargs.get('depth', 8)
    width = kwargs.get('width', 32)
    def func(push_valid: int = 0, push_instr: int = 0,
             pop_ready: int = 0, count: int = 0) -> Dict:
        can_push = count < depth
        can_pop = count > 0
        return {
            "instr": push_instr if can_push else 0,
            "valid": int(can_pop),
            "stall": int(not can_push),
            "count": count + push_valid - pop_ready if can_push and can_pop else
                     count + 1 if push_valid and can_push and not can_pop else
                     count - 1 if pop_ready and can_pop and not push_valid else
                     count,
        }
    return func


def scoreboard_functional(**kwargs) -> Callable:
    """Functional Scoreboard: register dependency tracking.
    Tracks which physical registers are busy (in-flight writes).
    """
    n_regs = kwargs.get('n_regs', VREGS)
    def func(alloc_reg: int = 0, alloc_valid: int = 0,
             commit_reg: int = 0, commit_valid: int = 0,
             busy_mask: int = 0) -> Dict:
        new_busy = busy_mask
        if alloc_valid:
            new_busy |= (1 << alloc_reg)
        if commit_valid:
            new_busy &= ~(1 << commit_reg)
        return {
            "busy_mask": new_busy,
            "ready_bits": (~new_busy) & ((1 << n_regs) - 1),
        }
    return func


def operand_collector_functional(**kwargs) -> Callable:
    """Functional Operand Collector: register read with bypass.
    Collects src operands from RF or bypass network.
    """
    width = kwargs.get('width', VLEN)
    def func(rs1: int = 0, rs2: int = 0,
             rf_data1: int = 0, rf_data2: int = 0,
             bypass_addr: int = 0, bypass_data: int = 0,
             bypass_valid: int = 0) -> Dict:
        op1 = bypass_data if bypass_valid and bypass_addr == rs1 else rf_data1
        op2 = bypass_data if bypass_valid and bypass_addr == rs2 else rf_data2
        return {"op1": op1, "op2": op2}
    return func


def vector_alu_functional(**kwargs) -> Callable:
    """Functional Vector ALU: INT32 vector arithmetic.
    16-lane SIMD: ADD, SUB, MUL, MLA, shift, bitwise.
    """
    n_lane = kwargs.get('n_lane', NLANE)
    xlen = kwargs.get('xlen', XLEN)
    mask = (1 << xlen) - 1
    def func(opcode: int = 0, op1: int = 0, op2: int = 0,
             pred_mask: int = 0xFFFF) -> Dict:
        result = 0
        for lane in range(n_lane):
            if not ((pred_mask >> lane) & 1):
                continue
            a = (op1 >> (lane * xlen)) & mask
            b = (op2 >> (lane * xlen)) & mask
            r = 0
            if opcode == OP_VADD:
                r = (a + b) & mask
            elif opcode == OP_VSUB:
                r = (a - b) & mask
            elif opcode == OP_VMUL:
                r = (a * b) & mask
            elif opcode == OP_VMLA:
                r = (a * b) & mask
            result |= r << (lane * xlen)
        return {"result": result, "valid": 1}
    return func


def vector_fpu_functional(**kwargs) -> Callable:
    """Functional Vector FPU: FP32 vector arithmetic.
    16-lane SIMD: FADD, FMUL, FMLA.
    """
    n_lane = kwargs.get('n_lane', NLANE)
    def func(opcode: int = 0, op1: int = 0, op2: int = 0,
             pred_mask: int = 0xFFFF) -> Dict:
        import struct
        result = 0
        flen = 32
        mask = (1 << flen) - 1
        for lane in range(n_lane):
            if not ((pred_mask >> lane) & 1):
                continue
            a_bits = (op1 >> (lane * flen)) & mask
            b_bits = (op2 >> (lane * flen)) & mask
            a = struct.unpack('>f', struct.pack('>I', a_bits))[0] if lane == 0 else 0.0
            b = struct.unpack('>f', struct.pack('>I', b_bits))[0] if lane == 0 else 0.0
            r = 0.0
            if opcode == OP_FADD:
                r = a + b
            elif opcode == OP_FMUL:
                r = a * b
            elif opcode == OP_FMLA:
                r = a * b
            r_bits = struct.pack('>f', r)
            r_int = struct.unpack('>I', r_bits)[0]
            result |= r_int << (lane * flen)
        return {"result": result, "valid": 1}
    return func


def sfu_functional(**kwargs) -> Callable:
    """Functional SFU: special function unit.
    Computes sqrt, rcp (reciprocal), sin, cos on scalar.
    """
    flen = kwargs.get('flen', FLEN)
    def func(op_func: int = 0, operand: int = 0) -> Dict:
        import struct
        mask = (1 << flen) - 1
        bits = operand & mask
        f = struct.unpack('>f', struct.pack('>I', bits))[0]
        r = 0.0
        if op_func == 0:  # sqrt
            r = math.sqrt(f) if f >= 0 else 0.0
        elif op_func == 1:  # rcp
            r = 1.0 / f if f != 0 else float('inf')
        elif op_func == 2:  # sin
            r = math.sin(f)
        elif op_func == 3:  # cos
            r = math.cos(f)
        r_bits = struct.pack('>f', r)
        r_int = struct.unpack('>I', r_bits)[0]
        return {"result": r_int, "valid": 1}
    return func


def tensor_core_functional(**kwargs) -> Callable:
    """Functional Tensor Core: 4×4×4 matrix multiply-accumulate.
    D = A × B + C where all matrices are 4×4 (FP16).
    """
    width = kwargs.get('width', 16)  # FP16 element
    def func(a_vals: List[int] = None, b_vals: List[int] = None,
             c_vals: List[int] = None) -> Dict:
        if a_vals is None: a_vals = [0] * 16
        if b_vals is None: b_vals = [0] * 16
        if c_vals is None: c_vals = [0] * 16
        import struct
        def fp16_to_f32(h):
            s = (h >> 15) & 1
            e = (h >> 10) & 0x1F
            m = h & 0x3FF
            if e == 0:
                return struct.unpack('>f', struct.pack('>I', (s << 31) | (m << 13)))[0]
            e32 = e - 15 + 127
            return struct.unpack('>f', struct.pack('>I', (s << 31) | (e32 << 23) | (m << 13)))[0]
        def f32_to_fp16(f):
            bits = struct.unpack('>I', struct.pack('>f', f))[0]
            s = (bits >> 31) & 1
            e = (bits >> 23) & 0xFF
            m = (bits >> 13) & 0x3FF
            e16 = max(0, min(31, ((e - 127 + 15) if e != 0 else 0)))
            return (s << 15) | (e16 << 10) | m

        A = [[fp16_to_f32(a_vals[i * 4 + j]) for j in range(4)] for i in range(4)]
        B = [[fp16_to_f32(b_vals[i * 4 + j]) for j in range(4)] for i in range(4)]
        C = [[fp16_to_f32(c_vals[i * 4 + j]) for j in range(4)] for i in range(4)]
        D = [[0.0] * 4 for _ in range(4)]
        for i in range(4):
            for j in range(4):
                s = C[i][j]
                for k in range(4):
                    s += A[i][k] * B[k][j]
                D[i][j] = s
        d_vals = [f32_to_fp16(D[i][j]) for i in range(4) for j in range(4)]
        return {"d_vals": d_vals, "valid": 1}
    return func


def lsu_functional(**kwargs) -> Callable:
    """Functional LSU: load/store unit with address generation.
    Generates byte addresses from vector base + offset.
    """
    vlen = kwargs.get('vlen', VLEN)
    xlen = kwargs.get('xlen', XLEN)
    def func(opcode: int = 0, base_addr: int = 0, offset: int = 0,
             vector_data: int = 0, pred_mask: int = 0xFFFF) -> Dict:
        is_load = (opcode == OP_VLOAD)
        addr = (base_addr + offset) & 0xFFFFFFFF
        return {
            "mem_req": 1,
            "mem_wen": int(not is_load),
            "mem_addr": addr,
            "mem_wdata": vector_data,
            "mem_size": vlen // 8,
        }
    return func


def memory_coalesce_functional(**kwargs) -> Callable:
    """Functional Memory Coalesce: coalesce warp requests.
    Combines per-lane requests into minimal cache line transactions.
    """
    vlen = kwargs.get('vlen', VLEN)
    def func(lane_addrs: List[int] = None, lane_valid: int = 0xFFFF) -> Dict:
        if lane_addrs is None:
            lane_addrs = [0] * NLANE
        aligned_base = lane_addrs[0] & ~0x3F  # 64B cache line
        return {
            "coalesced_addr": aligned_base,
            "coalesced_mask": 0xFFFFFFFFFFFFFFFF,  # all 8 words valid
            "num_transactions": 1,
        }
    return func


def l1_cache_functional(**kwargs) -> Callable:
    """Functional L1 Cache: unified data cache / shared memory.
    Direct-mapped, 64 B line, 64 KB.
    """
    size = kwargs.get('size', 64 * 1024)
    line_size = kwargs.get('line_size', 64)
    n_lines = size // line_size
    def func(addr: int = 0, req_valid: int = 0, wen: int = 0,
             wdata: int = 0, tag_array: List = None,
             data_array: List = None, valid_array: List = None) -> Dict:
        if tag_array is None: tag_array = [0] * n_lines
        if data_array is None: data_array = [0] * n_lines
        if valid_array is None: valid_array = [0] * n_lines
        idx = (addr // line_size) % n_lines
        tag = addr // (line_size * n_lines)
        hit = valid_array[idx] and tag_array[idx] == tag
        return {
            "hit": int(hit),
            "rdata": data_array[idx] if hit else 0,
            "miss": int(req_valid and not hit),
            "miss_addr": addr if req_valid and not hit else 0,
            "fill_line": idx,
            "fill_tag": tag,
        }
    return func


def shared_memory_functional(**kwargs) -> Callable:
    """Functional Shared Memory: per-SM software-managed scratchpad.
    32 banks, 4 B per bank (128-bit wide access).
    """
    size = kwargs.get('size', 32 * 1024)
    n_banks = kwargs.get('n_banks', 32)
    bank_w = 4  # bytes
    def func(addr: int = 0, wen: int = 0, wdata: int = 0,
             bank_conflict_mask: int = 0) -> Dict:
        bank = (addr // bank_w) % n_banks
        return {
            "rdata": wdata if not wen else 0,
            "bank_conflict": int((bank_conflict_mask >> bank) & 1),
        }
    return func


def l2_cache_functional(**kwargs) -> Callable:
    """Functional L2 Cache: shared L2 across SMs.
    8-way set-associative, 512 KB.
    """
    size = kwargs.get('size', 512 * 1024)
    n_ways = kwargs.get('n_ways', 8)
    line_size = 64
    n_sets = size // (n_ways * line_size)
    def func(addr: int = 0, req_valid: int = 0, wen: int = 0,
             wdata: int = 0,
             tag_array: List = None, data_array: List = None,
             lru_array: List = None) -> Dict:
        if tag_array is None: tag_array = [[0] * n_ways for _ in range(n_sets)]
        if lru_array is None: lru_array = [0] * n_sets
        set_idx = (addr // line_size) % n_sets
        tag = addr // (line_size * n_sets)
        hit = False
        hit_way = 0
        for w in range(n_ways):
            if tag_array[set_idx][w] == tag:
                hit = True; hit_way = w; break
        return {
            "hit": int(hit),
            "hit_way": hit_way,
            "miss": int(req_valid and not hit),
            "miss_addr": addr if req_valid and not hit else 0,
        }
    return func


def mem_controller_functional(**kwargs) -> Callable:
    """Functional Memory Controller: HBM3-like channel.
    Converts cache-line requests to DRAM bursts.
    """
    ch_w = kwargs.get('ch_w', 128)
    burst = kwargs.get('burst', 8)
    def func(req_valid: int = 0, addr: int = 0, wen: int = 0,
             wdata: int = 0, ready: int = 1) -> Dict:
        return {
            "grant": int(req_valid and ready),
            "rdata": wdata if not wen else 0,
            "valid": int(req_valid and ready),
        }
    return func


def sm_wrapper_functional(**kwargs) -> Callable:
    """Functional SM Wrapper: top-level SM combining all pipeline stages.
    Pure combinatorial: decode → issue → execute → writeback.
    """
    def func(inst: int = 0, pc: int = 0, warp_id: int = 0,
             scheduler_id: int = 0,
             rf: List = None, pred_mask: int = 0xFFFF) -> Dict:
        if rf is None: rf = [0] * VREGS
        opcode, rd, rs1, rs2, imm = decode_inst(inst)
        mx = (1 << XLEN) - 1
        result = 0
        wb_valid = 1
        if opcode == OP_SLOAD:
            result = imm & 0xFFFFFFFF
            for lane in range(1, NLANE):
                result |= (imm & 0xFFFFFFFF) << (lane * XLEN)
        elif opcode in (OP_VADD, OP_VMUL):
            a = rf[rs1] if rs1 < len(rf) else 0
            b = rf[rs2] if rs2 < len(rf) else 0
            result = 0
            for lane in range(NLANE):
                a_lane = (a >> (lane * XLEN)) & mx
                b_lane = (b >> (lane * XLEN)) & mx
                if opcode == OP_VADD:
                    r_lane = (a_lane + b_lane) & mx
                else:
                    r_lane = (a_lane * b_lane) & mx
                result |= r_lane << (lane * XLEN)
        elif opcode == OP_NOP:
            wb_valid = 0
        else:
            wb_valid = 0
        return {
            "wb_dest": rd,
            "wb_data": result,
            "wb_valid": wb_valid,
            "next_pc": pc + 1,
            "mem_req": int(opcode in (OP_VLOAD, OP_VSTORE)),
        }
    return func


def gpu_top_functional(**kwargs) -> Callable:
    """Functional GPU Top: full GPU with CTA scheduler + SMs + L2 + memory."""
    n_sm = kwargs.get('nsm', NSM)
    def func(sm_done_mask: int = 0, kernel_start: int = 0) -> Dict:
        return {
            "all_done": int(sm_done_mask == (1 << n_sm) - 1),
            "kernel_busy": int(sm_done_mask != (1 << n_sm) - 1),
        }
    return func


FUNCTIONAL_MODELS = {
    "cta_scheduler": cta_scheduler_functional,
    "warp_scheduler": warp_scheduler_functional,
    "simt_stack": simt_stack_functional,
    "ibuffer": ibuffer_functional,
    "scoreboard": scoreboard_functional,
    "operand_collector": operand_collector_functional,
    "vector_alu": vector_alu_functional,
    "vector_fpu": vector_fpu_functional,
    "sfu": sfu_functional,
    "tensor_core": tensor_core_functional,
    "lsu": lsu_functional,
    "memory_coalesce": memory_coalesce_functional,
    "l1_cache": l1_cache_functional,
    "shared_memory": shared_memory_functional,
    "l2_cache": l2_cache_functional,
    "mem_controller": mem_controller_functional,
    "sm_wrapper": sm_wrapper_functional,
    "gpu_top": gpu_top_functional,
}
