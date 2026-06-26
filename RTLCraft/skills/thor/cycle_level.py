"""
skills/thor/cycle_level — Layer 2: Cycle-accurate models.

Register-accurate pipeline timing for each Thor GPU pipeline stage.
"""
from __future__ import annotations
import math
from typing import Any, Callable, Dict, List, Optional, Tuple
from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry

from skills.thor import (
    XLEN, FLEN, NLANE, VLEN, VREGS, NWARP, N_SCHED, WARP_PER_SCHED,
    NSM, IMEM_DEPTH, N_ALU, N_FPU, N_SFU, N_TENSOR, N_LSU,
    OP_NOP, OP_SLOAD, OP_VLOAD, OP_VSTORE, OP_VADD, OP_VSUB,
    OP_VMUL, OP_VMLA, OP_FADD, OP_FMUL, OP_FMLA, OP_SFU,
    OP_TENSOR, OP_BARRIER, OP_DONE, OP_BRA, OP_SYNC,
    SIMT_STACK_DEPTH, decode_inst,
)


def cta_scheduler_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate CTA Scheduler: workgroup dispatch.
    State: per-SM CTA queue, dispatch pointer.
    """
    n_sm = kwargs.get('nsm', NSM)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['dispatch_ptr'] = 0
            ctx.state['sm_cta_count'] = [0] * n_sm
            ctx.state['kernel_active'] = 0
            return
        num_ctas = ctx.get_input('num_ctas', 0)
        sm_ready = ctx.get_input('sm_ready_mask', (1 << n_sm) - 1)
        kernel_start = ctx.get_input('kernel_start', 0)
        if kernel_start:
            ctx.state['kernel_active'] = 1
            ctx.state['dispatch_ptr'] = 0
            ctx.state['sm_cta_count'] = [0] * n_sm
        dispatched = 0
        if ctx.state.get('kernel_active', 0):
            ptr = ctx.state.get('dispatch_ptr', 0)
            for i in range(n_sm):
                sm = (ptr + i) % n_sm
                if (sm_ready >> sm) & 1:
                    cta_cnt = list(ctx.state.get('sm_cta_count', [0] * n_sm))
                    cta_cnt[sm] += 1
                    ctx.state['sm_cta_count'] = cta_cnt
                    ctx.state['dispatch_ptr'] = (sm + 1) % n_sm
                    ctx.set_output('dispatched_sm', sm)
                    ctx.set_output('dispatch_valid', 1)
                    dispatched = 1
                    break
            if dispatched and all(c >= num_ctas for c in ctx.state.get('sm_cta_count', [])):
                ctx.state['kernel_active'] = 0
        if not dispatched:
            ctx.set_output('dispatch_valid', 0)
        ctx.set_output('remaining_ctas',
                       max(0, num_ctas - sum(ctx.state.get('sm_cta_count', [0] * n_sm))))
    return behavior


def warp_scheduler_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate Warp Scheduler: round-robin with state.
    State: last_selected warp per scheduler.
    """
    n_warps = kwargs.get('n_warps', WARP_PER_SCHED)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['last_warp'] = 0
            return
        warp_ready = ctx.get_input('warp_ready_mask', 0)
        warp_stall = ctx.get_input('warp_stall_mask', 0)
        avail = warp_ready & ~warp_stall
        last = ctx.state.get('last_warp', 0)
        sel = last; valid = 0
        if avail:
            for i in range(n_warps):
                idx = (last + 1 + i) % n_warps
                if (avail >> idx) & 1:
                    sel = idx; valid = 1; break
            ctx.state['last_warp'] = sel
        ctx.set_output('selected_warp', sel)
        ctx.set_output('select_valid', valid)
    return behavior


def simt_stack_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate SIMT Stack: branch divergence with push/pop."""
    depth = kwargs.get('depth', SIMT_STACK_DEPTH)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['stack'] = []
            ctx.state['active_mask'] = 0xFFFF
            return
        push = ctx.get_input('push', 0)
        pop = ctx.get_input('pop', 0)
        ft_pc = ctx.get_input('fallthrough_pc', 0)
        br_pc = ctx.get_input('branch_pc', 0)
        rv_pc = ctx.get_input('reconv_pc', 0)
        pred = ctx.get_input('predicate_mask', 0)
        stack = list(ctx.state.get('stack', []))
        active = ctx.state.get('active_mask', 0xFFFF)
        if push and len(stack) < depth:
            stack.append({
                "reconv_pc": rv_pc, "ft_pc": ft_pc,
                "saved_active": active, "saved_pred": pred,
            })
            active &= pred
        elif pop and len(stack) > 0:
            entry = stack.pop()
            active = entry["saved_active"]
        ctx.state['stack'] = stack
        ctx.state['active_mask'] = active
        ctx.set_output('active_mask', active)
        ctx.set_output('reconv_pc', stack[-1]["reconv_pc"] if stack else 0)
        ctx.set_output('stack_empty', int(len(stack) == 0))
    return behavior


def ibuffer_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate IBuffer: instruction buffer with FIFO state."""
    depth = kwargs.get('depth', 8)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['wr'] = 0; ctx.state['rd'] = 0; ctx.state['cnt'] = 0
            for i in range(depth): ctx.state[f'mem_{i}'] = 0
            return
        push_v = ctx.get_input('push_valid', 0)
        push_d = ctx.get_input('push_data', 0)
        pop_r = ctx.get_input('pop_ready', 0)
        cnt = ctx.state.get('cnt', 0)
        wr = ctx.state.get('wr', 0)
        rd = ctx.state.get('rd', 0)
        push_ok = push_v and cnt < depth
        pop_ok = pop_r and cnt > 0
        if push_ok:
            ctx.state[f'mem_{wr}'] = push_d
            ctx.state['wr'] = (wr + 1) % depth
        if pop_ok:
            ctx.state['rd'] = (rd + 1) % depth
        if push_ok and not pop_ok:
            ctx.state['cnt'] = cnt + 1
        elif pop_ok and not push_ok:
            ctx.state['cnt'] = cnt - 1
        ctx.set_output('instr', ctx.state.get(f'mem_{rd}', 0))
        ctx.set_output('valid', int(cnt > 0))
        ctx.set_output('stall', int(cnt >= depth))
        ctx.set_output('count', ctx.state.get('cnt', 0))
    return behavior


def scoreboard_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate Scoreboard: register dependency tracking with state."""
    n_regs = kwargs.get('n_regs', VREGS)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['busy_mask'] = 0
            return
        busy = ctx.state.get('busy_mask', 0)
        alloc_r = ctx.get_input('alloc_reg', 0)
        alloc_v = ctx.get_input('alloc_valid', 0)
        commit_r = ctx.get_input('commit_reg', 0)
        commit_v = ctx.get_input('commit_valid', 0)
        if alloc_v: busy |= (1 << alloc_r)
        if commit_v: busy &= ~(1 << commit_r)
        ctx.state['busy_mask'] = busy
        ctx.set_output('busy_mask', busy)
        ctx.set_output('ready_bits', (~busy) & ((1 << n_regs) - 1))
    return behavior


def vector_alu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate Vector ALU: 2-stage pipelined INT32 vector ALU."""
    n_lane = kwargs.get('n_lane', NLANE)
    xlen = kwargs.get('xlen', XLEN)
    mask = (1 << xlen) - 1
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['pipe_val'] = 0
            return
        opcode = ctx.get_input('opcode', 0)
        op1 = ctx.get_input('op1', 0)
        op2 = ctx.get_input('op2', 0)
        pred = ctx.get_input('pred_mask', 0xFFFF)
        result = 0
        for lane in range(n_lane):
            if not ((pred >> lane) & 1): continue
            a = (op1 >> (lane * xlen)) & mask
            b = (op2 >> (lane * xlen)) & mask
            r = 0
            if opcode == OP_VADD: r = (a + b) & mask
            elif opcode == OP_VSUB: r = (a - b) & mask
            elif opcode == OP_VMUL: r = (a * b) & mask
            result |= r << (lane * xlen)
        ctx.state['pipe_val'] = result
        ctx.set_output('result', ctx.state.get('pipe_val', 0))
        ctx.set_output('valid', 1)
    return behavior


def lsu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate LSU: load/store with multi-cycle memory access."""
    vlen = kwargs.get('vlen', VLEN)
    xlen = kwargs.get('xlen', XLEN)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['pending'] = 0
            ctx.state['wait_valid'] = 0
            return
        opcode = ctx.get_input('opcode', 0)
        base = ctx.get_input('base_addr', 0)
        offset = ctx.get_input('offset', 0)
        wdata = ctx.get_input('vector_data', 0)
        mem_valid = ctx.get_input('mem_data_valid', 0)
        pending = ctx.state.get('pending', 0)
        wait_v = ctx.state.get('wait_valid', 0)
        is_load = (opcode == OP_VLOAD)
        addr = (base + offset) & 0xFFFFFFFF
        req = 0; wen = 0
        if not pending and not wait_v:
            if opcode in (OP_VLOAD, OP_VSTORE):
                req = 1; pending = 1
                if not is_load: wen = 1
        if pending:
            if mem_valid:
                pending = 0
                if is_load: ctx.state['load_data'] = ctx.get_input('mem_rdata', 0)
                else: wait_v = 0
            else:
                wait_v = 1
        ctx.state['pending'] = pending
        ctx.state['wait_valid'] = wait_v
        ctx.set_output('mem_req', req)
        ctx.set_output('mem_wen', wen)
        ctx.set_output('mem_addr', addr)
        ctx.set_output('mem_wdata', wdata)
        ctx.set_output('rd_data', ctx.state.get('load_data', 0))
        ctx.set_output('rd_valid', int(not pending and wait_v == 0 and opcode in (OP_VLOAD, OP_VSTORE)))
    return behavior


def l1_cache_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate L1 Cache: direct-mapped with state."""
    size = kwargs.get('size', 64 * 1024)
    line_size = 64
    n_lines = size // line_size
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            for i in range(n_lines):
                ctx.state[f'tag_{i}'] = 0
                ctx.state[f'data_{i}'] = 0
                ctx.state[f'valid_{i}'] = 0
            ctx.state['miss_pending'] = 0
            return
        addr = ctx.get_input('addr', 0)
        req_v = ctx.get_input('req_valid', 0)
        wen = ctx.get_input('wen', 0)
        wdata = ctx.get_input('wdata', 0)
        fill_v = ctx.get_input('fill_valid', 0)
        fill_d = ctx.get_input('fill_data', 0)
        fill_idx = ctx.get_input('fill_line', 0)
        miss_p = ctx.state.get('miss_pending', 0)
        idx = (addr // line_size) % n_lines
        tag = addr // (line_size * n_lines)
        tag_key = f'tag_{idx}'
        vld_key = f'valid_{idx}'
        dat_key = f'data_{idx}'
        tag_r = ctx.state.get(tag_key, 0)
        vld_r = ctx.state.get(vld_key, 0)
        hit = vld_r and tag_r == tag
        ctx.set_output('hit', int(hit))
        if hit:
            ctx.set_output('rdata', ctx.state.get(dat_key, 0))
        else:
            ctx.set_output('rdata', 0)
        ctx.set_output('miss', int(req_v and not hit))
        ctx.set_output('miss_addr', addr if req_v and not hit else 0)
        if fill_v:
            ctx.state[dat_key] = fill_d
            ctx.state[vld_key] = 1
            ctx.state[tag_key] = fill_idx
        if wen and hit:
            ctx.state[dat_key] = wdata
    return behavior


def sm_wrapper_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate SM Wrapper: full SM with warp FSM pipeline.
    
    5-stage in-order warp pipeline:
      F: Fetch   - read IMEM
      D: Decode  - decode instruction
      E: Execute - ALU/FPU/LSU/SFU/Tensor
      M: Memory  - cache access
      W: Writeback - register write
    """
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['cycle'] = 0
            ctx.state['running'] = 0
            for w in range(NWARP):
                ctx.state[f'warp_pc_{w}'] = 0
                ctx.state[f'warp_state_{w}'] = 0  # 0=idle,1=fetch,2=decode,3=exec,4=mem,5=wb
                ctx.state[f'warp_done_{w}'] = 0
                ctx.state[f'warp_inst_{w}'] = 0
            ctx.state['warp_sel'] = 0
            ctx.state['wb_dest'] = 0
            ctx.state['wb_data'] = 0
            ctx.state['wb_valid'] = 0
            return

        start = ctx.get_input('start', 0)
        imem = [ctx.get_input(f'imem_{i}', 0) for i in range(IMEM_DEPTH)]
        wb_accept = ctx.get_input('wb_accept', 1)
        mem_rdata = ctx.get_input('mem_rdata', 0)
        mem_rdy = ctx.get_input('mem_ready', 1)
        mem_v = ctx.get_input('mem_valid', 0)

        cycle = ctx.state.get('cycle', 0) + 1
        ctx.state['cycle'] = cycle

        if start and not ctx.state.get('running', 0):
            ctx.state['running'] = 1
            for w in range(NWARP):
                ctx.state[f'warp_pc_{w}'] = 0
                ctx.state[f'warp_state_{w}'] = 0
                ctx.state[f'warp_done_{w}'] = 0

        # 5-stage warp pipeline (single-issue, round-robin)
        warp_sel = ctx.state.get('warp_sel', 0)

        # Stage 5: Writeback (from previous cycle's execute)
        wb_valid = ctx.state.get('wb_valid', 0)
        if wb_valid and wb_accept:
            rd_dest = ctx.state.get('wb_dest', 0)
            rd_data = ctx.state.get('wb_data', 0)
            # Write to VRF indexed by current warp
            ctx.state[f'vrf_{warp_sel}_{rd_dest}'] = rd_data
            ctx.state['wb_valid'] = 0

        # Stage 4: Memory (from decode stage)
        mem_req = 0; mem_wen = 0; mem_addr = 0; mem_wdata = 0
        wb_data = 0; wb_dest = 0; wb_val = 0

        # Find a warp in fetch state
        ctx.state['warp_sel'] = (warp_sel + 1) % NWARP
        for w in range(NWARP):
            ws = ctx.state.get(f'warp_state_{w}', 0)
            if ws == 0:  # idle -> fetch
                if ctx.state.get('running', 0) and not ctx.state.get(f'warp_done_{w}', 0):
                    ctx.state[f'warp_state_{w}'] = 1
                    ctx.state['warp_sel'] = w
                    break

        # Execute selected warp
        w = ctx.state.get('warp_sel', 0)
        ws = ctx.state.get(f'warp_state_{w}', 0)
        inst = ctx.state.get(f'warp_inst_{w}', 0)

        if ws == 1:  # Fetch
            pc = ctx.state.get(f'warp_pc_{w}', 0)
            fetched = imem[pc % IMEM_DEPTH]
            ctx.state[f'warp_inst_{w}'] = fetched
            ctx.state[f'warp_pc_{w}'] = (pc + 1) % IMEM_DEPTH
            ctx.state[f'warp_state_{w}'] = 2

        elif ws == 2:  # Decode
            opcode, rd, rs1, rs2, imm = decode_inst(inst)
            ctx.state['wb_dest'] = rd
            ctx.state['wb_data'] = 0
            if opcode == OP_SLOAD:
                vec = imm & 0xFFFFFFFF
                for lane in range(1, NLANE):
                    vec |= (imm & 0xFFFFFFFF) << (lane * XLEN)
                ctx.state['wb_data'] = vec
                ctx.state['wb_valid'] = 1
                ctx.state[f'warp_state_{w}'] = 0
            elif opcode in (OP_VADD, OP_VMUL):
                a = ctx.state.get(f'vrf_{w}_{rs1}', 0)
                b = ctx.state.get(f'vrf_{w}_{rs2}', 0)
                if opcode == OP_VADD:
                    ctx.state['wb_data'] = (a + b) & ((1 << VLEN) - 1)
                else:
                    ctx.state['wb_data'] = (a * b) & ((1 << VLEN) - 1)
                ctx.state['wb_valid'] = 1
                ctx.state[f'warp_state_{w}'] = 0
            elif opcode == OP_DONE:
                ctx.state[f'warp_done_{w}'] = 1
                ctx.state[f'warp_state_{w}'] = 0xF
            elif opcode in (OP_VLOAD, OP_VSTORE):
                mem_req = 1
                mem_wen = int(opcode == OP_VSTORE)
                mem_addr = imm & 0xFFFFFFFF
                mem_wdata = ctx.state.get(f'vrf_{w}_{rs1}', 0)
                ctx.state[f'warp_state_{w}'] = 3
            elif opcode == OP_BARRIER:
                ctx.state[f'warp_state_{w}'] = 0
            else:
                ctx.state[f'warp_state_{w}'] = 0

        elif ws == 3:  # Memory wait
            if mem_v and mem_rdy:
                if not mem_wen:  # load
                    ctx.state['wb_data'] = mem_rdata
                    ctx.state['wb_valid'] = 1
                    ctx.state['wb_dest'] = ctx.state.get('wb_dest', 0)
                ctx.state[f'warp_state_{w}'] = 0

        elif ws == 0xF:  # Done (holds state)
            pass

        # Memory outputs
        ctx.set_output('mem_req', mem_req)
        ctx.set_output('mem_wen', mem_wen)
        ctx.set_output('mem_addr', mem_addr)
        ctx.set_output('mem_wdata', mem_wdata)

        # SM done detection
        all_done = all(ctx.state.get(f'warp_done_{ww}', 0) for ww in range(NWARP))
        ctx.set_output('sm_done', int(all_done))
    return behavior


# =====================================================================
# Template Registry
# =====================================================================
TemplateRegistry.register('cta_scheduler', cta_scheduler_cycle)
TemplateRegistry.register('warp_scheduler', warp_scheduler_cycle)
TemplateRegistry.register('simt_stack', simt_stack_cycle)
TemplateRegistry.register('ibuffer', ibuffer_cycle)
TemplateRegistry.register('scoreboard', scoreboard_cycle)
TemplateRegistry.register('vector_alu', vector_alu_cycle)
TemplateRegistry.register('lsu', lsu_cycle)
TemplateRegistry.register('l1_cache', l1_cache_cycle)
TemplateRegistry.register('sm_wrapper', sm_wrapper_cycle)

# Aliases
cta_scheduler_template = cta_scheduler_cycle
warp_scheduler_template = warp_scheduler_cycle
simt_stack_template = simt_stack_cycle
ibuffer_template = ibuffer_cycle
scoreboard_template = scoreboard_cycle
vector_alu_template = vector_alu_cycle
lsu_template = lsu_cycle
l1_cache_template = l1_cache_cycle
sm_wrapper_template = sm_wrapper_cycle
