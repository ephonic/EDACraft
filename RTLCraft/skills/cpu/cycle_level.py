"""
skills/cpu.cycle_level — Layer 2 cycle-accurate models.

Pipeline timing and register-accurate behavior for each subsystem.
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry
from rtlgen.behaviors import fifo_template, datapath_template


def ifu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate IFU model (3-stage fetch pipeline)."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['pc'] = 0x1000
            ctx.state['if1_valid'] = 0; ctx.state['if2_valid'] = 0
            ctx.state['if3_valid'] = 0
            return
        ctx.state['if3_valid'] = ctx.state.get('if2_valid', 0)
        ctx.state['if2_valid'] = ctx.state.get('if1_valid', 0)
        ctx.state['if1_valid'] = 1
        ctx.state['pc'] = ctx.state.get('pc', 0x1000) + 8
        ctx.set_output('fetch_valid', ctx.state['if3_valid'])
    return behavior


def iu_alu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate ALU model (2-stage pipeline)."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['pipe'] = 0; return
        src0 = ctx.get_input('src0', 0); src1 = ctx.get_input('src1', 0)
        ctx.state['pipe'] = src0 + src1
        ctx.set_output('result', ctx.state.get('pipe', 0))
    return behavior


def ibuf_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate IBuf model (FIFO + bypass)."""
    depth = kwargs.get('depth', 8)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['cnt'] = 0; ctx.state['wr'] = 0; ctx.state['rd'] = 0
            return
        push_v = ctx.get_input('push_valid', 0)
        push_d = ctx.get_input('push_data', 0)
        pop_r = ctx.get_input('pop_ready', 0)
        cnt = ctx.state.get('cnt', 0); wr = ctx.state.get('wr', 0); rd = ctx.state.get('rd', 0)
        mem = ctx.state.get('mem', {})
        # Outputs use current state
        ctx.set_output('data', push_d if push_v else mem.get(rd, 0))
        ctx.set_output('valid', cnt > 0)
        ctx.set_output('stall', cnt >= depth)
        # State update
        push_ok = push_v & (cnt < depth)
        pop_ok = pop_r & (cnt > 0)
        if push_ok:
            new_mem = dict(mem)
            new_mem[wr] = push_d
            ctx.state['mem'] = new_mem
            wr = (wr + 1) % depth
        if pop_ok:
            rd = (rd + 1) % depth
        # HDL non-blocking: pop (last assignment) overwrites push
        if pop_ok:
            cnt = cnt - 1
        elif push_ok:
            cnt = cnt + 1
        ctx.state['cnt'] = cnt; ctx.state['wr'] = wr; ctx.state['rd'] = rd
    return behavior


TemplateRegistry.register('ifu', ifu_cycle)
TemplateRegistry.register('iu_alu', iu_alu_cycle)
TemplateRegistry.register('ibuf', ibuf_cycle)


# =====================================================================
# IFU Sub-Module L2 Cycle-Accurate Models
# =====================================================================

def pcgen_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for PCGen (PC generation unit)."""
    PW = kwargs.get('PC_WIDTH', 39)
    RV = kwargs.get('RESET_VEC', 0)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['pc'] = RV
            ctx.state['init'] = 0
            return
        init = ctx.state.get('init', 0)
        pc = ctx.state.get('pc', RV)
        rv = ctx.get_input('rv', 0)
        rpc = ctx.get_input('rpc', 0)
        stall = ctx.get_input('stall', 0)
        if init == 0:
            ctx.state['init'] = 1
            any_rv = False
            if not stall:
                ctx.state['pc'] = pc + 4
            new_pc = ctx.state.get('pc', pc)
            ctx.set_output('pc', new_pc)
            ctx.set_output('pc_chg', 1 if any_rv else 0)
            return
        any_rv = (rv != 0)
        target = 0
        for i in range(9):
            if (rv >> i) & 1:
                target = (rpc >> (i * PW)) & ((1 << PW) - 1)
                break
        if any_rv:
            ctx.state['pc'] = target
        elif not stall:
            ctx.state['pc'] = pc + 4
        new_pc = ctx.state.get('pc', pc)
        ctx.set_output('pc', new_pc)
        ctx.set_output('pc_chg', 1 if any_rv else 0)
    return behavior


def bpred_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for BPred (gshare + BTB + RAS)."""
    XL = kwargs.get('XLEN', 64)
    RD = kwargs.get('RAS_DEPTH', 8)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            ctx.state['ghr'] = 0
            ctx.state['ras_ptr'] = 0
            ctx.state['ras_stack'] = {}
            return
        init = ctx.state.get('init', 0)
        req_pc = ctx.get_input('req_pc', 0)
        req_valid = ctx.get_input('req_valid', 0)
        upd_pc = ctx.get_input('upd_pc', 0)
        upd_taken = ctx.get_input('upd_taken', 0)
        upd_valid = ctx.get_input('upd_valid', 0)
        upd_is_call = ctx.get_input('upd_is_call', 0)
        upd_is_return = ctx.get_input('upd_is_return', 0)
        if init == 0:
            ctx.state['init'] = 1
            ctx.set_output('pred_taken', 0)
            ctx.set_output('pred_target', 0)
            ctx.set_output('pred_valid', 0)
            return
        ghr = ctx.state.get('ghr', 0)
        ras_ptr = ctx.state.get('ras_ptr', 0)
        pht = ctx.state.get('pht', {})
        btb_valid = ctx.state.get('btb_valid', {})
        btb_target = ctx.state.get('btb_target', {})
        ras_stack = ctx.state.get('ras_stack', {})
        pht_idx = ((req_pc >> 3) ^ ghr) & 0xFFF
        counter = pht.get(pht_idx, 0)
        btb_idx = (req_pc >> 3) & 0x3FF
        btb_hit = btb_valid.get(btb_idx, 0)
        if ras_ptr != 0:
            ras_target = ras_stack.get(ras_ptr - 1, 0)
        else:
            ras_target = 0
        pred_taken = 1 if counter >= 2 else 0
        pred_target = btb_target.get(btb_idx, 0)
        pred_valid = btb_hit & req_valid
        ctx.set_output('pred_taken', pred_taken)
        ctx.set_output('pred_target', pred_target)
        ctx.set_output('pred_valid', pred_valid)
        if (upd_valid == 1) & (upd_taken == 1):
            ghr = ((ghr << 1) | 1) & 0xFFF
        elif upd_valid == 1:
            ghr = (ghr << 1) & 0xFFF
        if upd_is_call == 1:
            new_stack = dict(ras_stack)
            new_stack[ras_ptr] = upd_pc + 4
            ctx.state['ras_stack'] = new_stack
            ras_ptr = (ras_ptr + 1) % RD
        elif (upd_is_return == 1) & (ras_ptr != 0):
            ras_ptr = (ras_ptr - 1) % RD
        ctx.state['ghr'] = ghr
        ctx.state['ras_ptr'] = ras_ptr
    return behavior


def addrgen_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for AddrGen (fetch address generation)."""
    PW = kwargs.get('PC_WIDTH', 39)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            return
        init = ctx.state.get('init', 0)
        pc = ctx.get_input('pc', 0)
        redirect = ctx.get_input('redirect', 0)
        redirect_pc = ctx.get_input('redirect_pc', 0)
        stall = ctx.get_input('stall', 0)
        if init == 0:
            ctx.state['init'] = 1
            ctx.set_output('fetch_addr', 0)
            ctx.set_output('fetch_valid', 0)
            return
        fetch_addr = redirect_pc if redirect else pc
        ctx.set_output('fetch_addr', fetch_addr)
        ctx.set_output('fetch_valid', 0 if stall else 1)
    return behavior


def icache_if_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for ICacheIF (L1 I-cache interface)."""
    PW = kwargs.get('ADDR_WIDTH', 39)
    DW = kwargs.get('DATA_WIDTH', 64)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            ctx.state['pending'] = 0
            ctx.state['miss_r'] = 0
            return
        init = ctx.state.get('init', 0)
        pending = ctx.state.get('pending', 0)
        miss_r = ctx.state.get('miss_r', 0)
        req_valid = ctx.get_input('req_valid', 0)
        cache_rdata = ctx.get_input('cache_rdata', 0)
        cache_ready = ctx.get_input('cache_ready', 0)
        flush = ctx.get_input('flush', 0)
        if init == 0:
            ctx.state['init'] = 1
            if (req_valid == 1) & (pending == 0):
                pending = 1; miss_r = 0
            if cache_ready == 1:
                pending = 0
            if flush == 1:
                pending = 0
            ctx.state['pending'] = pending
            ctx.state['miss_r'] = miss_r
            ctx.set_output('req_ready', 0 if pending else 1)
            ctx.set_output('rdata', cache_rdata)
            ctx.set_output('rvalid', 1 if (cache_ready == 1) & (pending == 1) else 0)
            ctx.set_output('miss', miss_r)
            return
        if (req_valid == 1) & (pending == 0):
            pending = 1; miss_r = 0
        if cache_ready == 1:
            pending = 0
        if flush == 1:
            pending = 0
        ctx.state['pending'] = pending
        ctx.state['miss_r'] = miss_r
        ctx.set_output('req_ready', 0 if pending else 1)
        ctx.set_output('rdata', cache_rdata)
        ctx.set_output('rvalid', 1 if (cache_ready == 1) & (pending == 1) else 0)
        ctx.set_output('miss', miss_r)
    return behavior


def ifctrl_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for IFCtrl (fetch control)."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            return
        init = ctx.state.get('init', 0)
        branch_taken = ctx.get_input('branch_taken', 0)
        branch_target = ctx.get_input('branch_target', 0)
        icache_miss = ctx.get_input('icache_miss', 0)
        ibuf_full = ctx.get_input('ibuf_full', 0)
        flush = ctx.get_input('flush', 0)
        if init == 0:
            ctx.state['init'] = 1
            ctx.set_output('redirect', 0)
            ctx.set_output('redirect_pc', 0)
            ctx.set_output('stall_fetch', 0)
            return
        ctx.set_output('redirect', 1 if (branch_taken == 1) | (flush == 1) else 0)
        ctx.set_output('redirect_pc', branch_target)
        ctx.set_output('stall_fetch', 1 if (icache_miss == 1) | (ibuf_full == 1) else 0)
    return behavior


def lbuf_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for LBuf (loop buffer)."""
    W = kwargs.get('WIDTH', 32)
    E = kwargs.get('ENTRIES', 16)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            ctx.state['mem'] = {}
            ctx.state['vld'] = {}
            return
        init = ctx.state.get('init', 0)
        fill = ctx.get_input('fill', 0)
        fill_data = ctx.get_input('fill_data', 0)
        fill_idx = ctx.get_input('fill_idx', 0)
        loop_active = ctx.get_input('loop_active', 0)
        loop_start = ctx.get_input('loop_start', 0)
        loop_end = ctx.get_input('loop_end', 0)
        rd_idx = ctx.get_input('rd_idx', 0)
        if init == 0:
            ctx.state['init'] = 1
            ctx.set_output('rdata', 0)
            ctx.set_output('rhit', 0)
            return
        mem = ctx.state.get('mem', {})
        vld = ctx.state.get('vld', {})
        if fill == 1:
            new_mem = dict(mem); new_vld = dict(vld)
            new_mem[fill_idx] = fill_data; new_vld[fill_idx] = 1
            mem = new_mem; vld = new_vld
            ctx.state['mem'] = mem; ctx.state['vld'] = vld
        rdata = mem.get(rd_idx, 0)
        rhit = 1 if (loop_active == 1) & vld.get(rd_idx, 0) & (rd_idx >= loop_start) & (rd_idx <= loop_end) else 0
        ctx.set_output('rdata', rdata)
        ctx.set_output('rhit', rhit)
    return behavior


def ind_btb_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for IndirectBranchBTB."""
    E = kwargs.get('ENTRIES', 8)
    XL = kwargs.get('XLEN', 39)
    IW = max(E.bit_length() - 1, 1)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            ctx.state['tag'] = {}
            ctx.state['tgt'] = {}
            ctx.state['vld'] = {}
            return
        init = ctx.state.get('init', 0)
        req_pc = ctx.get_input('req_pc', 0)
        req_valid = ctx.get_input('req_valid', 0)
        upd_pc = ctx.get_input('upd_pc', 0)
        upd_target = ctx.get_input('upd_target', 0)
        upd_valid = ctx.get_input('upd_valid', 0)
        if init == 0:
            ctx.state['init'] = 1
            ctx.set_output('pred_target', 0)
            ctx.set_output('pred_valid', 0)
            return
        tag = ctx.state.get('tag', {})
        tgt = ctx.state.get('tgt', {})
        vld = ctx.state.get('vld', {})
        if upd_valid == 1:
            uidx = (upd_pc >> 2) & ((1 << IW) - 1)
            new_tag = dict(tag); new_tgt = dict(tgt); new_vld = dict(vld)
            new_tag[uidx] = upd_pc >> (2 + IW)
            new_tgt[uidx] = upd_target
            new_vld[uidx] = 1
            tag = new_tag; tgt = new_tgt; vld = new_vld
            ctx.state['tag'] = tag; ctx.state['tgt'] = tgt; ctx.state['vld'] = vld
        idx = (req_pc >> 2) & ((1 << IW) - 1)
        tag_r = tag.get(idx, 0)
        hit = vld.get(idx, 0) & (tag_r == (req_pc >> (2 + IW)))
        ctx.set_output('pred_target', tgt.get(idx, 0))
        ctx.set_output('pred_valid', 1 if (hit == 1) & (req_valid == 1) else 0)
    return behavior


def predecode_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for PreDecodeBuffer."""
    D = kwargs.get('DEPTH', 4)
    W = kwargs.get('WIDTH', 32)
    TW = kwargs.get('TAG_WIDTH', 8)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['wr'] = 0; ctx.state['rd'] = 0
            ctx.state['cnt'] = 0; ctx.state['bp_v'] = 0
            ctx.state['mem_i'] = {}; ctx.state['mem_t'] = {}
            ctx.state['bp_i'] = 0; ctx.state['bp_t'] = 0
            return
        init = ctx.state.get('init', 0)
        wr = ctx.state.get('wr', 0); rd = ctx.state.get('rd', 0)
        cnt = ctx.state.get('cnt', 0); bp_v = ctx.state.get('bp_v', 0)
        mem_i = ctx.state.get('mem_i', {}); mem_t = ctx.state.get('mem_t', {})
        bp_i = ctx.state.get('bp_i', 0); bp_t = ctx.state.get('bp_t', 0)
        push_valid = ctx.get_input('push_valid', 0)
        push_instr = ctx.get_input('push_instr', 0)
        push_tag = ctx.get_input('push_tag', 0)
        pop_ready = ctx.get_input('pop_ready', 0)
        flush = ctx.get_input('flush', 0)
        if init == 0:
            ctx.state['init'] = 1
            if not flush:
                push_ok = (push_valid == 1) & (cnt < D)
                pop_ok = (pop_ready == 1) & (cnt > 0)
                if push_ok:
                    new_mi = dict(mem_i); new_mt = dict(mem_t)
                    new_mi[wr] = push_instr; new_mt[wr] = push_tag
                    ctx.state['mem_i'] = new_mi; ctx.state['mem_t'] = new_mt
                    mem_i = new_mi; mem_t = new_mt
                    wr = (wr + 1) % D
                if pop_ok:
                    rd = (rd + 1) % D
                if pop_ok:
                    cnt = cnt - 1
                elif push_ok:
                    cnt = cnt + 1
                if (push_valid == 1) & (pop_ready == 0):
                    bp_v = 1; bp_i = push_instr; bp_t = push_tag
                elif pop_ready == 1:
                    bp_v = 0
                ctx.state['wr'] = wr; ctx.state['rd'] = rd; ctx.state['cnt'] = cnt
                ctx.state['bp_v'] = bp_v; ctx.state['bp_i'] = bp_i; ctx.state['bp_t'] = bp_t
            f_v = (cnt != 0)
            if f_v:
                ctx.set_output('instr', mem_i.get(rd, 0))
                ctx.set_output('tag', mem_t.get(rd, 0))
                ctx.set_output('valid', 1)
            elif bp_v:
                ctx.set_output('instr', bp_i)
                ctx.set_output('tag', bp_t)
                ctx.set_output('valid', 1)
            else:
                ctx.set_output('instr', 0); ctx.set_output('tag', 0)
                ctx.set_output('valid', 0)
            ctx.set_output('stall', 1 if (cnt >= D) & (push_valid == 1) else 0)
            ctx.set_output('free_slots', D - cnt)
            return
        # State update for next cycle
        if flush == 1:
            wr = 0; rd = 0; cnt = 0; bp_v = 0
        else:
            push_ok = (push_valid == 1) & (cnt < D)
            pop_ok = (pop_ready == 1) & (cnt > 0)
            if push_ok:
                new_mi = dict(mem_i); new_mt = dict(mem_t)
                new_mi[wr] = push_instr; new_mt[wr] = push_tag
                ctx.state['mem_i'] = new_mi; ctx.state['mem_t'] = new_mt
                mem_i = new_mi; mem_t = new_mt
                wr = (wr + 1) % D
            if pop_ok:
                rd = (rd + 1) % D
            if pop_ok:
                cnt = cnt - 1
            elif push_ok:
                cnt = cnt + 1
            if (push_valid == 1) & (pop_ready == 0):
                bp_v = 1; bp_i = push_instr; bp_t = push_tag
            elif pop_ready == 1:
                bp_v = 0
        ctx.state['wr'] = wr; ctx.state['rd'] = rd; ctx.state['cnt'] = cnt
        ctx.state['bp_v'] = bp_v; ctx.state['bp_i'] = bp_i; ctx.state['bp_t'] = bp_t
        f_v = (cnt != 0)
        if f_v:
            ctx.set_output('instr', mem_i.get(rd, 0))
            ctx.set_output('tag', mem_t.get(rd, 0))
            ctx.set_output('valid', 1)
        elif bp_v:
            ctx.set_output('instr', bp_i)
            ctx.set_output('tag', bp_t)
            ctx.set_output('valid', 1)
        else:
            ctx.set_output('instr', 0); ctx.set_output('tag', 0)
            ctx.set_output('valid', 0)
        ctx.set_output('stall', 1 if (cnt >= D) & (push_valid == 1) else 0)
        ctx.set_output('free_slots', D - cnt)
    return behavior


def pcfifo_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for PCFifo."""
    D = kwargs.get('DEPTH', 8)
    XL = kwargs.get('XLEN', 39)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['wr'] = 0
            ctx.state['rd'] = 0; ctx.state['cnt'] = 0
            ctx.state['mem'] = {}
            return
        init = ctx.state.get('init', 0)
        wr = ctx.state.get('wr', 0); rd = ctx.state.get('rd', 0)
        cnt = ctx.state.get('cnt', 0); mem = ctx.state.get('mem', {})
        push_pc = ctx.get_input('push_pc', 0)
        push_valid = ctx.get_input('push_valid', 0)
        pop = ctx.get_input('pop', 0)
        flush = ctx.get_input('flush', 0)
        if init == 0:
            ctx.state['init'] = 1
            if not flush:
                push_ok = (push_valid == 1) & (cnt < D)
                pop_ok = (pop == 1) & (cnt > 0)
                if push_ok:
                    new_mem = dict(mem)
                    new_mem[wr] = push_pc
                    ctx.state['mem'] = new_mem
                    mem = new_mem
                    wr = (wr + 1) % D
                if pop_ok:
                    rd = (rd + 1) % D
                if pop_ok:
                    cnt = cnt - 1
                elif push_ok:
                    cnt = cnt + 1
                ctx.state['wr'] = wr; ctx.state['rd'] = rd
                ctx.state['cnt'] = cnt
            ctx.set_output('top_pc', mem.get(rd, 0))
            ctx.set_output('top_valid', 1 if cnt != 0 else 0)
            ctx.set_output('free', D - cnt)
            return
        if flush == 1:
            wr = 0; rd = 0; cnt = 0
        else:
            push_ok = (push_valid == 1) & (cnt < D)
            pop_ok = (pop == 1) & (cnt > 0)
            if push_ok:
                new_mem = dict(mem)
                new_mem[wr] = push_pc
                ctx.state['mem'] = new_mem
                mem = new_mem
                wr = (wr + 1) % D
            if pop_ok:
                rd = (rd + 1) % D
            if pop_ok:
                cnt = cnt - 1
            elif push_ok:
                cnt = cnt + 1
        ctx.state['wr'] = wr; ctx.state['rd'] = rd
        ctx.state['cnt'] = cnt
        ctx.set_output('top_pc', mem.get(rd, 0))
        ctx.set_output('top_valid', 1 if cnt != 0 else 0)
        ctx.set_output('free', D - cnt)
    return behavior


def vec_fetch_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for VectorFetch."""
    XL = kwargs.get('XLEN', 39)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['active'] = 0
            ctx.state['cur_pc'] = 0; ctx.state['count'] = 0
            return
        init = ctx.state.get('init', 0)
        start = ctx.get_input('start', 0)
        start_pc = ctx.get_input('start_pc', 0)
        vlen = ctx.get_input('vlen', 0)
        fetch_ready = ctx.get_input('fetch_ready', 0)
        active = ctx.state.get('active', 0)
        cur_pc = ctx.state.get('cur_pc', 0)
        count = ctx.state.get('count', 0)
        if init == 0:
            ctx.state['init'] = 1
            if (start == 1) & (active == 0):
                ctx.state['active'] = 1
                ctx.state['cur_pc'] = start_pc
                ctx.state['count'] = vlen
                active = 1; cur_pc = start_pc; count = vlen
            ctx.set_output('fetch_addr', cur_pc)
            ctx.set_output('fetch_valid', 1 if (active == 1) & (fetch_ready == 1) else 0)
            ctx.set_output('busy', 1 if active else 0)
            ctx.set_output('done', 1 if (active == 1) & (count <= 1) & (fetch_ready == 1) else 0)
            return
        if (start == 1) & (active == 0):
            active = 1; cur_pc = start_pc; count = vlen
        elif (active == 1) & (fetch_ready == 1):
            if count > 1:
                cur_pc = cur_pc + 4; count = count - 1
            else:
                active = 0; count = 0
        ctx.state['active'] = active
        ctx.state['cur_pc'] = cur_pc
        ctx.state['count'] = count
        ctx.set_output('fetch_addr', cur_pc)
        ctx.set_output('fetch_valid', 1 if (active == 1) & (fetch_ready == 1) else 0)
        ctx.set_output('busy', 1 if active else 0)
        ctx.set_output('done', 1 if (active == 1) & (count <= 1) & (fetch_ready == 1) else 0)
    return behavior


def l1_refill_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for L1Refill (cache refill FSM)."""
    LW = kwargs.get('LINE_WORDS', 4)
    AW = kwargs.get('ADDR_WIDTH', 39)
    IDLE = 0; REQ = 1; FILL = 2
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['state'] = IDLE
            ctx.state['burst_cnt'] = 0; ctx.state['base_addr'] = 0
            ctx.state['done_r'] = 0
            return
        init = ctx.state.get('init', 0)
        state = ctx.state.get('state', IDLE)
        burst_cnt = ctx.state.get('burst_cnt', 0)
        base_addr = ctx.state.get('base_addr', 0)
        done_r = 0
        miss_addr = ctx.get_input('miss_addr', 0)
        miss_valid = ctx.get_input('miss_valid', 0)
        l2_rdata = ctx.get_input('l2_rdata', 0)
        l2_ready = ctx.get_input('l2_ready', 0)
        if init == 0:
            ctx.state['init'] = 1
            if miss_valid == 1:
                ctx.state['state'] = REQ
                ctx.state['base_addr'] = miss_addr
                ctx.state['burst_cnt'] = LW
                state = REQ; base_addr = miss_addr; burst_cnt = LW
            ctx.set_output('refill_addr', base_addr)
            ctx.set_output('refill_req', 1 if state == REQ else 0)
            ctx.set_output('refill_data', l2_rdata)
            ctx.set_output('refill_done', done_r)
            ctx.set_output('busy', 1 if state != IDLE else 0)
            return
        state = ctx.state.get('state', IDLE)
        burst_cnt = ctx.state.get('burst_cnt', 0)
        base_addr = ctx.state.get('base_addr', 0)
        done_r = 0
        if state == IDLE:
            if miss_valid == 1:
                state = REQ; base_addr = miss_addr; burst_cnt = LW
        elif state == REQ:
            state = FILL
        elif state == FILL:
            if l2_ready == 1:
                if burst_cnt > 1:
                    burst_cnt = burst_cnt - 1
                else:
                    state = IDLE; burst_cnt = 0; done_r = 1
        ctx.state['state'] = state
        ctx.state['burst_cnt'] = burst_cnt
        ctx.state['base_addr'] = base_addr
        ctx.state['done_r'] = done_r
        ctx.set_output('refill_addr', base_addr)
        ctx.set_output('refill_req', 1 if state == REQ else 0)
        ctx.set_output('refill_data', l2_rdata)
        ctx.set_output('refill_done', done_r)
        ctx.set_output('busy', 1 if state != IDLE else 0)
    return behavior


def sfp_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for SFP (speculation flush predict)."""
    MD = kwargs.get('MAX_DEPTH', 8)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['depth'] = 0
            return
        init = ctx.state.get('init', 0)
        branch_taken = ctx.get_input('branch_taken', 0)
        branch_mispredict = ctx.get_input('branch_mispredict', 0)
        flush_external = ctx.get_input('flush_external', 0)
        redirect = ctx.get_input('redirect', 0)
        if init == 0:
            ctx.state['init'] = 1
            ctx.set_output('flush', 0); ctx.set_output('flush_redirect', 0)
            ctx.set_output('spec_depth', 0)
            return
        depth = ctx.state.get('depth', 0)
        if branch_mispredict == 1:
            depth = 0
        elif (branch_taken == 1) & (depth < MD - 1):
            depth = depth + 1
        elif (branch_taken == 0) & (depth > 0):
            depth = depth - 1
        ctx.state['depth'] = depth
        ctx.set_output('flush', 1 if (branch_mispredict == 1) | (flush_external == 1) else 0)
        ctx.set_output('flush_redirect', 1 if redirect == 1 else 0)
        ctx.set_output('spec_depth', depth)
    return behavior


def ifu_debug_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 cycle-accurate model for IFUDebug (debug counters)."""
    CW = kwargs.get('COUNTER_WIDTH', 32)
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['c_fetch'] = 0
            ctx.state['c_icache'] = 0; ctx.state['c_branch'] = 0
            ctx.state['c_flush'] = 0
            return
        init = ctx.state.get('init', 0)
        c_fetch = ctx.state.get('c_fetch', 0)
        c_icache = ctx.state.get('c_icache', 0)
        c_branch = ctx.state.get('c_branch', 0)
        c_flush = ctx.state.get('c_flush', 0)
        fetch_valid = ctx.get_input('fetch_valid', 0)
        icache_miss = ctx.get_input('icache_miss', 0)
        branch_taken = ctx.get_input('branch_taken', 0)
        flush = ctx.get_input('flush', 0)
        if init == 0:
            ctx.state['init'] = 1
            if fetch_valid == 1:
                c_fetch = c_fetch + 1
            if icache_miss == 1:
                c_icache = c_icache + 1
            if branch_taken == 1:
                c_branch = c_branch + 1
            if flush == 1:
                c_flush = c_flush + 1
            ctx.state['c_fetch'] = c_fetch
            ctx.state['c_icache'] = c_icache
            ctx.state['c_branch'] = c_branch
            ctx.state['c_flush'] = c_flush
            ctx.set_output('fetched_instrs', c_fetch)
            ctx.set_output('icache_misses', c_icache)
            ctx.set_output('branches', c_branch)
            ctx.set_output('flushes', c_flush)
            return
        if fetch_valid == 1:
            c_fetch = c_fetch + 1
        if icache_miss == 1:
            c_icache = c_icache + 1
        if branch_taken == 1:
            c_branch = c_branch + 1
        if flush == 1:
            c_flush = c_flush + 1
        ctx.state['c_fetch'] = c_fetch
        ctx.state['c_icache'] = c_icache
        ctx.state['c_branch'] = c_branch
        ctx.state['c_flush'] = c_flush
        ctx.set_output('fetched_instrs', c_fetch)
        ctx.set_output('icache_misses', c_icache)
        ctx.set_output('branches', c_branch)
        ctx.set_output('flushes', c_flush)
    return behavior


# =====================================================================
# IFU Sub-Module Registry
# =====================================================================

TemplateRegistry.register('pcgen', pcgen_cycle)
TemplateRegistry.register('bpred', bpred_cycle)
TemplateRegistry.register('addrgen', addrgen_cycle)
TemplateRegistry.register('icache_if', icache_if_cycle)
TemplateRegistry.register('ifctrl', ifctrl_cycle)
TemplateRegistry.register('lbuf', lbuf_cycle)
TemplateRegistry.register('ind_btb', ind_btb_cycle)
TemplateRegistry.register('predecode', predecode_cycle)
TemplateRegistry.register('pcfifo', pcfifo_cycle)
TemplateRegistry.register('vec_fetch', vec_fetch_cycle)
TemplateRegistry.register('l1_refill', l1_refill_cycle)
TemplateRegistry.register('sfp', sfp_cycle)
TemplateRegistry.register('ifu_debug', ifu_debug_cycle)


# =====================================================================
# IDU Sub-Module L2 Cycle-Accurate Models (14 classes)
# =====================================================================


def decoder_cycle(**kwargs):
    """L2 cycle-accurate model for Decoder."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        ctx.state['init'] = 1
        instr = ctx.get_input('instr', 0)
        op = instr & 0x7F
        ctx.set_output('opcode', op)
        ctx.set_output('rd', (instr >> 7) & 0x1F)
        ctx.set_output('rs1', (instr >> 15) & 0x1F)
        ctx.set_output('rs2', (instr >> 20) & 0x1F)
        ctx.set_output('funct3', (instr >> 12) & 0x7)
        ctx.set_output('funct7', (instr >> 25) & 0x7F)
        ctx.set_output('is_imm', 1 if (op != 0x33 and op != 0x3B) else 0)
        imm_val = 0
        if op in (0x13, 0x03, 0x67, 0x73, 0x1B):
            imm_val = (instr >> 20) & 0xFFF
            if imm_val >> 11: imm_val |= 0xFFFFFFFFFFFFF000
        elif op == 0x23:
            imm_val = ((instr >> 25) << 5) | ((instr >> 7) & 0x1F)
            if imm_val >> 11: imm_val |= 0xFFFFFFFFFFFFF000
        elif op == 0x63:
            imm_val = (((instr >> 31) & 1) << 12) | (((instr >> 7) & 1) << 11) | (((instr >> 25) & 0x3F) << 5) | (((instr >> 8) & 0xF) << 1)
            if imm_val >> 12: imm_val |= 0xFFFFFFFFFFFFE000
        elif op in (0x37, 0x17):
            imm_val = instr & 0xFFFFFFFFFFFFF000
        elif op == 0x6F:
            imm_val = (((instr >> 31) & 1) << 20) | (((instr >> 12) & 0xFF) << 12) | (((instr >> 20) & 1) << 11) | (((instr >> 21) & 0x3FF) << 1)
            if imm_val >> 20: imm_val |= 0xFFFFFFFFFFE00000
        ctx.set_output('imm', imm_val & 0xFFFFFFFFFFFFFFFF)
    return behavior


def ir_ctrl_cycle(**kwargs):
    """L2 cycle-accurate model for IRCtrl."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        ctx.state['init'] = 1
        alloc_req = ctx.get_input('alloc_req', 0)
        freelist_empty = ctx.get_input('freelist_empty', 0)
        ctx.set_output('alloc_grant', 1 if (alloc_req == 1) and (freelist_empty == 0) else 0)
        ctx.set_output('stall', 1 if (alloc_req == 1) and (freelist_empty == 1) else 0)
    return behavior


def is_ctrl_cycle(**kwargs):
    """L2 cycle-accurate model for ISCtrl (round-robin arbiter)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['pointer'] = 0
            ctx.state['grant_idx_r'] = 0; ctx.state['grant_valid_r'] = 0
            return
        init = ctx.state.get('init', 0)
        pointer = ctx.state.get('pointer', 0)
        ready_mask = ctx.get_input('ready_mask', 0)
        grant_any = ctx.get_input('grant_any', 0)

        def rr_select(rm, ptr):
            for i in range(4):
                idx = (ptr + i) & 3
                if (rm >> idx) & 1:
                    return idx
            return (ptr + 3) & 3

        if init == 0:
            next_grant_idx = 0; next_grant_valid = 0
        else:
            next_grant_idx = rr_select(ready_mask, pointer)
            has_any = ((ready_mask & 0xF) != 0)
            next_grant_valid = 1 if (grant_any == 1) and has_any else 0

        ctx.state['init'] = 1
        ctx.state['grant_idx_r'] = next_grant_idx
        ctx.state['grant_valid_r'] = next_grant_valid
        if (next_grant_valid == 1) and (grant_any == 1) and (init == 1):
            ctx.state['pointer'] = (pointer + 1) & 3

        ctx.set_output('grant_idx', ctx.state.get('grant_idx_r', 0))
        ctx.set_output('grant_valid', ctx.state.get('grant_valid_r', 0))
    return behavior


def sdiq_cycle(**kwargs):
    """L2 cycle-accurate model for SDIQ."""
    pr_num = kwargs.get('pr_num', 64)
    entries = 4
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0; ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['op_t'] = {}; ctx.state['prd_t'] = {}; ctx.state['prs1_t'] = {}
            ctx.state['prs2_t'] = {}; ctx.state['rdy1_t'] = {}; ctx.state['rdy2_t'] = {}; ctx.state['vld_t'] = {}
            return
        init = ctx.state.get('init', 0)
        head = ctx.state.get('head', 0); tail = ctx.state.get('tail', 0); cnt = ctx.state.get('cnt', 0)
        op_t = dict(ctx.state.get('op_t', {})); prd_t = dict(ctx.state.get('prd_t', {}))
        prs1_t = dict(ctx.state.get('prs1_t', {})); prs2_t = dict(ctx.state.get('prs2_t', {}))
        rdy1_t = dict(ctx.state.get('rdy1_t', {})); rdy2_t = dict(ctx.state.get('rdy2_t', {})); vld_t = dict(ctx.state.get('vld_t', {}))
        flush = ctx.get_input('flush', 0); enqueue = ctx.get_input('enqueue', 0)
        prs1 = ctx.get_input('prs1', 0); prs2 = ctx.get_input('prs2', 0)
        prd = ctx.get_input('prd', 0); op = ctx.get_input('op', 0)
        wakeup_pr = ctx.get_input('wakeup_pr', 0); wakeup_en = ctx.get_input('wakeup_en', 0)
        issue_ready = ctx.get_input('issue_ready', 0)
        ctx.state['init'] = 1
        if flush == 1:
            head = 0; tail = 0; cnt = 0; vld_t = {}
        else:
            if (enqueue == 1) and (cnt < entries):
                op_t[tail] = op; prd_t[tail] = prd; prs1_t[tail] = prs1; prs2_t[tail] = prs2
                rdy1_t[tail] = 0; rdy2_t[tail] = 0; vld_t[tail] = 1
                tail = (tail + 1) & 3; cnt += 1
            if wakeup_en == 1:
                for i in range(entries):
                    if (vld_t.get(i, 0) == 1) and (prs1_t.get(i, 0) == wakeup_pr):
                        rdy1_t[i] = 1
                    if (vld_t.get(i, 0) == 1) and (prs2_t.get(i, 0) == wakeup_pr):
                        rdy2_t[i] = 1
            issue_cond = (issue_ready == 1) and (cnt > 0) and (vld_t.get(head, 0) == 1) and (rdy1_t.get(head, 0) == 1) and (rdy2_t.get(head, 0) == 1)
            if issue_cond:
                vld_t[head] = 0; head = (head + 1) & 3; cnt -= 1
        ctx.state['head'] = head; ctx.state['tail'] = tail; ctx.state['cnt'] = cnt
        ctx.state['op_t'] = op_t; ctx.state['prd_t'] = prd_t; ctx.state['prs1_t'] = prs1_t; ctx.state['prs2_t'] = prs2_t
        ctx.state['rdy1_t'] = rdy1_t; ctx.state['rdy2_t'] = rdy2_t; ctx.state['vld_t'] = vld_t
        ctx.set_output('issue_op', op_t.get(head, 0))
        ctx.set_output('issue_prd', prd_t.get(head, 0))
        v_ok = (cnt > 0) and (vld_t.get(head, 0) == 1) and (rdy1_t.get(head, 0) == 1) and (rdy2_t.get(head, 0) == 1)
        ctx.set_output('issue_valid', 1 if v_ok else 0)
        ctx.set_output('full', 1 if cnt >= entries else 0)
    return behavior


def viq_cycle(**kwargs):
    """L2 cycle-accurate model for VIQ."""
    pr_num = kwargs.get('pr_num', 64)
    entries = 4
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0; ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['op_t'] = {}; ctx.state['prd_t'] = {}; ctx.state['prs1_t'] = {}
            ctx.state['rdy1_t'] = {}; ctx.state['vld_t'] = {}
            return
        init = ctx.state.get('init', 0)
        head = ctx.state.get('head', 0); tail = ctx.state.get('tail', 0); cnt = ctx.state.get('cnt', 0)
        op_t = dict(ctx.state.get('op_t', {})); prd_t = dict(ctx.state.get('prd_t', {}))
        prs1_t = dict(ctx.state.get('prs1_t', {}))
        rdy1_t = dict(ctx.state.get('rdy1_t', {})); vld_t = dict(ctx.state.get('vld_t', {}))
        flush = ctx.get_input('flush', 0); enqueue = ctx.get_input('enqueue', 0)
        prs1 = ctx.get_input('prs1', 0); prd = ctx.get_input('prd', 0); op = ctx.get_input('op', 0)
        wakeup_pr = ctx.get_input('wakeup_pr', 0); wakeup_en = ctx.get_input('wakeup_en', 0)
        issue_ready = ctx.get_input('issue_ready', 0)
        ctx.state['init'] = 1
        if flush == 1:
            head = 0; tail = 0; cnt = 0; vld_t = {}
        else:
            if (enqueue == 1) and (cnt < entries):
                op_t[tail] = op; prd_t[tail] = prd; prs1_t[tail] = prs1
                rdy1_t[tail] = 0; vld_t[tail] = 1
                tail = (tail + 1) & 3; cnt += 1
            if wakeup_en == 1:
                for i in range(entries):
                    if (vld_t.get(i, 0) == 1) and (prs1_t.get(i, 0) == wakeup_pr):
                        rdy1_t[i] = 1
            issue_cond = (issue_ready == 1) and (cnt > 0) and (vld_t.get(head, 0) == 1) and (rdy1_t.get(head, 0) == 1)
            if issue_cond:
                vld_t[head] = 0; head = (head + 1) & 3; cnt -= 1
        ctx.state['head'] = head; ctx.state['tail'] = tail; ctx.state['cnt'] = cnt
        ctx.state['op_t'] = op_t; ctx.state['prd_t'] = prd_t; ctx.state['prs1_t'] = prs1_t
        ctx.state['rdy1_t'] = rdy1_t; ctx.state['vld_t'] = vld_t
        ctx.set_output('issue_op', op_t.get(head, 0))
        ctx.set_output('issue_prd', prd_t.get(head, 0))
        v_ok = (cnt > 0) and (vld_t.get(head, 0) == 1) and (rdy1_t.get(head, 0) == 1)
        ctx.set_output('issue_valid', 1 if v_ok else 0)
        ctx.set_output('full', 1 if cnt >= entries else 0)
    return behavior


def rf_write_ctrl_cycle(**kwargs):
    """L2 cycle-accurate model for RFWriteCtrl."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['prf'] = {}; return
        ctx.state['init'] = 1
        we = ctx.get_input('we', 0); busy = ctx.get_input('busy', 0)
        pr_waddr = ctx.get_input('pr_waddr', 0); pr_wdata = ctx.get_input('pr_wdata', 0)
        prf = dict(ctx.state.get('prf', {}))
        if (we == 1) and (busy == 0):
            prf[pr_waddr] = pr_wdata
        ctx.state['prf'] = prf
        ctx.set_output('ready', 1 if busy == 0 else 0)
    return behavior


def rf_read_ctrl_cycle(**kwargs):
    """L2 cycle-accurate model for RFReadCtrl."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        ctx.state['init'] = 1
        pr_addr1 = ctx.get_input('pr_addr1', 0); pr_addr2 = ctx.get_input('pr_addr2', 0)
        pr_waddr = ctx.get_input('pr_waddr', 0); pr_wdata = ctx.get_input('pr_wdata', 0)
        pr_we = ctx.get_input('pr_we', 0)
        fwd1 = (pr_we == 1) and (pr_addr1 == pr_waddr) and (pr_addr1 != 0)
        fwd2 = (pr_we == 1) and (pr_addr2 == pr_waddr) and (pr_addr2 != 0)
        ctx.set_output('rdata1', pr_wdata if fwd1 else 0)
        ctx.set_output('rdata2', pr_wdata if fwd2 else 0)
    return behavior


def prf_cycle(**kwargs):
    """L2 cycle-accurate model for PRF."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['regs'] = {}; return
        ctx.state['init'] = 1
        rd_addr1 = ctx.get_input('rd_addr1', 0); rd_addr2 = ctx.get_input('rd_addr2', 0)
        wr_addr = ctx.get_input('wr_addr', 0); wr_data = ctx.get_input('wr_data', 0)
        wr_en = ctx.get_input('wr_en', 0)
        regs = dict(ctx.state.get('regs', {}))
        if (wr_en == 1) and (wr_addr != 0):
            regs[wr_addr] = wr_data
        ctx.state['regs'] = regs
        ctx.set_output('rd_data1', 0 if rd_addr1 == 0 else regs.get(rd_addr1, 0))
        ctx.set_output('rd_data2', 0 if rd_addr2 == 0 else regs.get(rd_addr2, 0))
    return behavior


def fwd_net_cycle(**kwargs):
    """L2 cycle-accurate model for FwdNet."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        ctx.state['init'] = 1
        rd_addr1 = ctx.get_input('rd_addr1', 0); rd_addr2 = ctx.get_input('rd_addr2', 0)
        rd_data1_raw = ctx.get_input('rd_data1_raw', 0); rd_data2_raw = ctx.get_input('rd_data2_raw', 0)
        fwd0_addr = ctx.get_input('fwd0_addr', 0); fwd0_data = ctx.get_input('fwd0_data', 0); fwd0_en = ctx.get_input('fwd0_en', 0)
        fwd1_addr = ctx.get_input('fwd1_addr', 0); fwd1_data = ctx.get_input('fwd1_data', 0); fwd1_en = ctx.get_input('fwd1_en', 0)

        def fwd_port(ra, raw, f0a, f0d, f0e, f1a, f1d, f1e):
            if ra == 0: return 0
            if (f0e == 1) and (f0a == ra): return f0d
            if (f1e == 1) and (f1a == ra): return f1d
            return raw

        ctx.set_output('rd_data1', fwd_port(rd_addr1, rd_data1_raw, fwd0_addr, fwd0_data, fwd0_en, fwd1_addr, fwd1_data, fwd1_en))
        ctx.set_output('rd_data2', fwd_port(rd_addr2, rd_data2_raw, fwd0_addr, fwd0_data, fwd0_en, fwd1_addr, fwd1_data, fwd1_en))
    return behavior


def fence_unit_cycle(**kwargs):
    """L2 cycle-accurate model for FenceUnit (FENCE/FENCE.I FSM)."""
    IDLE = 0; DRAIN_ST = 1; IFENCE = 2; DONE = 3
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['state'] = IDLE; return
        init = ctx.state.get('init', 0)
        state = ctx.state.get('state', IDLE)
        enqueue = ctx.get_input('enqueue', 0)
        is_fence_i = ctx.get_input('is_fence_i', 0)
        store_buffer_drain = ctx.get_input('store_buffer_drain', 0)
        icache_flush_rdy = ctx.get_input('icache_flush_rdy', 0)

        if init == 0:
            next_state = IDLE
        else:
            if state == IDLE:
                next_state = DRAIN_ST if enqueue == 1 else IDLE
            elif state == DRAIN_ST:
                if store_buffer_drain == 1:
                    next_state = IFENCE if is_fence_i == 1 else DONE
                else:
                    next_state = DRAIN_ST
            elif state == IFENCE:
                next_state = DONE if icache_flush_rdy == 1 else IFENCE
            else:
                next_state = IDLE

        ctx.state['init'] = 1
        ctx.state['state'] = next_state
        ctx.set_output('busy', 1 if next_state != IDLE else 0)
        ctx.set_output('store_drain_req', 1 if next_state == DRAIN_ST else 0)
        ctx.set_output('icache_flush_req', 1 if next_state == IFENCE else 0)
        ctx.set_output('completed', 1 if next_state == DONE else 0)
    return behavior


def f_rename_table_cycle(**kwargs):
    """L2 cycle-accurate model for FRenameTable."""
    ar_num = kwargs.get('ar_num', 32); pr_num = kwargs.get('pr_num', 32)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['fl_head'] = 0; ctx.state['fl_cnt'] = 0
            map_t = {}; freelist = {}
            for i in range(ar_num): map_t[i] = min(i, pr_num - 1)
            for i in range(pr_num - ar_num): freelist[i] = ar_num + i
            ctx.state['map_t'] = map_t; ctx.state['freelist'] = freelist
            return
        map_t = dict(ctx.state.get('map_t', {}))
        freelist = dict(ctx.state.get('freelist', {}))
        fl_head = ctx.state.get('fl_head', 0); fl_cnt = ctx.state.get('fl_cnt', 0)
        frs1 = ctx.get_input('frs1', 0); frs2 = ctx.get_input('frs2', 0)
        frd = ctx.get_input('frd', 0); frd_phy = ctx.get_input('frd_phy', 0); frd_we = ctx.get_input('frd_we', 0)
        alloc = ctx.get_input('alloc', 0)
        ctx.state['init'] = 1
        if frd_we == 1: map_t[frd] = frd_phy
        if (alloc == 1) and (fl_cnt > 0):
            fl_head = fl_head + 1; fl_cnt = fl_cnt - 1
        ctx.state['map_t'] = map_t; ctx.state['fl_head'] = fl_head; ctx.state['fl_cnt'] = fl_cnt
        ctx.set_output('pfrs1', map_t.get(frs1, 0))
        ctx.set_output('pfrs2', map_t.get(frs2, 0))
        ctx.set_output('alloc_fphy', freelist.get(fl_head, 0))
        ctx.set_output('freelist_empty', 1 if fl_cnt == 0 else 0)
    return behavior


def v_rename_table_cycle(**kwargs):
    """L2 cycle-accurate model for VRenameTable."""
    ar_num = kwargs.get('ar_num', 32); pr_num = kwargs.get('pr_num', 32)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['fl_head'] = 0; ctx.state['fl_cnt'] = 0
            map_t = {}; freelist = {}
            for i in range(ar_num): map_t[i] = min(i, pr_num - 1)
            for i in range(pr_num - ar_num): freelist[i] = ar_num + i
            ctx.state['map_t'] = map_t; ctx.state['freelist'] = freelist
            return
        map_t = dict(ctx.state.get('map_t', {}))
        freelist = dict(ctx.state.get('freelist', {}))
        fl_head = ctx.state.get('fl_head', 0); fl_cnt = ctx.state.get('fl_cnt', 0)
        vrs1 = ctx.get_input('vrs1', 0); vrs2 = ctx.get_input('vrs2', 0)
        vrd = ctx.get_input('vrd', 0); vrd_phy = ctx.get_input('vrd_phy', 0); vrd_we = ctx.get_input('vrd_we', 0)
        alloc = ctx.get_input('alloc', 0)
        ctx.state['init'] = 1
        if vrd_we == 1: map_t[vrd] = vrd_phy
        if (alloc == 1) and (fl_cnt > 0):
            fl_head = fl_head + 1; fl_cnt = fl_cnt - 1
        ctx.state['map_t'] = map_t; ctx.state['fl_head'] = fl_head; ctx.state['fl_cnt'] = fl_cnt
        ctx.set_output('pvrs1', map_t.get(vrs1, 0))
        ctx.set_output('pvrs2', map_t.get(vrs2, 0))
        ctx.set_output('alloc_vphy', freelist.get(fl_head, 0))
        ctx.set_output('freelist_empty', 1 if fl_cnt == 0 else 0)
    return behavior


def rename_table_cycle(**kwargs):
    """L2 cycle-accurate model for RenameTable."""
    ar_num = kwargs.get('ar_num', 32); pr_num = kwargs.get('pr_num', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['fl_head'] = 0; ctx.state['fl_cnt'] = 0
            map_t = {}; freelist = {}
            for i in range(ar_num): map_t[i] = min(i, pr_num - 1)
            for i in range(pr_num - ar_num): freelist[i] = ar_num + i
            ctx.state['map_t'] = map_t; ctx.state['freelist'] = freelist
            return
        map_t = dict(ctx.state.get('map_t', {}))
        freelist = dict(ctx.state.get('freelist', {}))
        fl_head = ctx.state.get('fl_head', 0); fl_cnt = ctx.state.get('fl_cnt', 0)
        rs1 = ctx.get_input('rs1', 0); rs2 = ctx.get_input('rs2', 0)
        rd = ctx.get_input('rd', 0); rd_phy = ctx.get_input('rd_phy', 0); rd_we = ctx.get_input('rd_we', 0)
        alloc = ctx.get_input('alloc', 0)
        ctx.state['init'] = 1
        if rd_we == 1: map_t[rd] = rd_phy
        if (alloc == 1) and (fl_cnt > 0):
            fl_head = fl_head + 1; fl_cnt = fl_cnt - 1
        ctx.state['map_t'] = map_t; ctx.state['fl_head'] = fl_head; ctx.state['fl_cnt'] = fl_cnt
        ctx.set_output('prs1', map_t.get(rs1, 0))
        ctx.set_output('prs2', map_t.get(rs2, 0))
        ctx.set_output('alloc_phy', freelist.get(fl_head, 0))
        ctx.set_output('freelist_empty', 1 if fl_cnt == 0 else 0)
    return behavior


def issue_queue_cycle(**kwargs):
    """L2 cycle-accurate model for IssueQueue."""
    entries = kwargs.get('entries', 8)
    pr_num = kwargs.get('pr_num', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0; ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['op_t'] = {}; ctx.state['prd_t'] = {}; ctx.state['prs1_t'] = {}; ctx.state['prs2_t'] = {}
            ctx.state['rdy1_t'] = {}; ctx.state['rdy2_t'] = {}; ctx.state['vld_t'] = {}
            return
        head = ctx.state.get('head', 0); tail = ctx.state.get('tail', 0); cnt = ctx.state.get('cnt', 0)
        op_t = dict(ctx.state.get('op_t', {})); prd_t = dict(ctx.state.get('prd_t', {}))
        prs1_t = dict(ctx.state.get('prs1_t', {})); prs2_t = dict(ctx.state.get('prs2_t', {}))
        rdy1_t = dict(ctx.state.get('rdy1_t', {})); rdy2_t = dict(ctx.state.get('rdy2_t', {})); vld_t = dict(ctx.state.get('vld_t', {}))
        flush = ctx.get_input('flush', 0); enqueue = ctx.get_input('enqueue', 0)
        prs1 = ctx.get_input('prs1', 0); prs2 = ctx.get_input('prs2', 0)
        prd = ctx.get_input('prd', 0); op = ctx.get_input('op', 0)
        wakeup_pr = ctx.get_input('wakeup_pr', 0); wakeup_en = ctx.get_input('wakeup_en', 0)
        issue_ready = ctx.get_input('issue_ready', 0)
        ctx.state['init'] = 1
        if flush == 1:
            head = 0; tail = 0; cnt = 0; vld_t = {}
        else:
            if (enqueue == 1) and (cnt < entries):
                op_t[tail] = op; prd_t[tail] = prd; prs1_t[tail] = prs1; prs2_t[tail] = prs2
                rdy1_t[tail] = 0; rdy2_t[tail] = 0; vld_t[tail] = 1
                tail = (tail + 1) % entries; cnt += 1
            if wakeup_en == 1:
                for i in range(entries):
                    if (vld_t.get(i, 0) == 1) and (prs1_t.get(i, 0) == wakeup_pr): rdy1_t[i] = 1
                    if (vld_t.get(i, 0) == 1) and (prs2_t.get(i, 0) == wakeup_pr): rdy2_t[i] = 1
            rdy1_eff = (rdy1_t.get(head, 0) == 1) or (prs1_t.get(head, 0) == 0)
            rdy2_eff = (rdy2_t.get(head, 0) == 1) or (prs2_t.get(head, 0) == 0)
            issue_cond = (issue_ready == 1) and (cnt > 0) and (vld_t.get(head, 0) == 1) and rdy1_eff and rdy2_eff
            if issue_cond:
                vld_t[head] = 0; head = (head + 1) % entries; cnt -= 1
        ctx.state['head'] = head; ctx.state['tail'] = tail; ctx.state['cnt'] = cnt
        ctx.state['op_t'] = op_t; ctx.state['prd_t'] = prd_t
        ctx.state['prs1_t'] = prs1_t; ctx.state['prs2_t'] = prs2_t
        ctx.state['rdy1_t'] = rdy1_t; ctx.state['rdy2_t'] = rdy2_t; ctx.state['vld_t'] = vld_t
        ctx.set_output('issue_op', op_t.get(head, 0))
        ctx.set_output('issue_prd', prd_t.get(head, 0))
        rdy1_eff_o = (rdy1_t.get(head, 0) == 1) or (prs1_t.get(head, 0) == 0)
        rdy2_eff_o = (rdy2_t.get(head, 0) == 1) or (prs2_t.get(head, 0) == 0)
        v_ok = (cnt > 0) and (vld_t.get(head, 0) == 1) and rdy1_eff_o and rdy2_eff_o
        ctx.set_output('issue_valid', 1 if v_ok else 0)
        ctx.set_output('full', 1 if cnt >= entries else 0)
    return behavior


# =====================================================================
# IDU Sub-Module Registry
# =====================================================================

TemplateRegistry.register('decoder', decoder_cycle)
TemplateRegistry.register('ir_ctrl', ir_ctrl_cycle)
TemplateRegistry.register('is_ctrl', is_ctrl_cycle)
TemplateRegistry.register('sdiq', sdiq_cycle)
TemplateRegistry.register('viq', viq_cycle)
TemplateRegistry.register('rf_write_ctrl', rf_write_ctrl_cycle)
TemplateRegistry.register('rf_read_ctrl', rf_read_ctrl_cycle)
TemplateRegistry.register('prf', prf_cycle)
TemplateRegistry.register('fwd_net', fwd_net_cycle)
TemplateRegistry.register('fence_unit', fence_unit_cycle)
TemplateRegistry.register('f_rename_table', f_rename_table_cycle)
TemplateRegistry.register('v_rename_table', v_rename_table_cycle)
TemplateRegistry.register('rename_table', rename_table_cycle)
TemplateRegistry.register('issue_queue', issue_queue_cycle)


# =====================================================================
# IU Sub-Module L2 Cycle-Accurate Models (6 modules)
# =====================================================================


def bju_cycle(**kwargs):
    """L2 cycle-accurate model for BJU (branch/jump, combinational)."""
    W = kwargs.get('width', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.set_output('taken', 0); ctx.set_output('target', 0)
            return
        op = ctx.get_input('op', 0)
        a = ctx.get_input('a', 0) & ((1 << W) - 1)
        b = ctx.get_input('b', 0) & ((1 << W) - 1)
        pc = ctx.get_input('pc', 0) & ((1 << W) - 1)
        taken = 0; target = 0
        if op == 0:
            taken = 1 if a == b else 0
            target = pc + b
        elif op == 1:
            taken = 1 if a != b else 0
            target = pc + b
        elif op == 2:
            taken = 1
            target = pc + b
        elif op == 3:
            taken = 1
            target = (a + b) & ~1
        elif op == 4:
            target = pc + b
            a_s = a if a < (1 << (W-1)) else a - (1 << W)
            b_s = b if b < (1 << (W-1)) else b - (1 << W)
            taken = 1 if a_s < b_s else 0
        elif op == 5:
            target = pc + b
            a_s = a if a < (1 << (W-1)) else a - (1 << W)
            b_s = b if b < (1 << (W-1)) else b - (1 << W)
            taken = 1 if a_s >= b_s else 0
        elif op == 6:
            target = pc + b
            taken = 1 if a < b else 0
        elif op == 7:
            target = pc + b
            taken = 1 if a >= b else 0
        ctx.set_output('taken', taken)
        ctx.set_output('target', target & ((1 << W) - 1))
    return behavior


def result_bus_cycle(**kwargs):
    """L2 cycle-accurate model for ResultBus (single-entry result writeback)."""
    W = kwargs.get('width', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['valid_r'] = 0
            ctx.state['prd_r'] = 0; ctx.state['data_r'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('wb_valid', 0); ctx.set_output('wb_prd', 0)
            ctx.set_output('wb_data', 0); ctx.set_output('busy', 0)
            return
        valid_r = ctx.state.get('valid_r', 0)
        prd_r = ctx.state.get('prd_r', 0)
        data_r = ctx.state.get('data_r', 0)
        retire = ctx.get_input('retire', 0)
        complete = ctx.get_input('complete', 0)
        issue_valid = ctx.get_input('issue_valid', 0)
        issue_prd = ctx.get_input('issue_prd', 0)
        result = ctx.get_input('result', 0)
        if retire == 1:
            valid_r = 0
        if (complete == 1) and (issue_valid == 1):
            valid_r = 1
            prd_r = issue_prd
            data_r = result
        ctx.state['valid_r'] = valid_r
        ctx.state['prd_r'] = prd_r
        ctx.state['data_r'] = data_r
        ctx.set_output('wb_valid', valid_r)
        ctx.set_output('wb_prd', prd_r)
        ctx.set_output('wb_data', data_r)
        ctx.set_output('busy', valid_r)
    return behavior


def divider_cycle(**kwargs):
    """L2 cycle-accurate model for Divider (multi-cycle restoring)."""
    W = kwargs.get('width', 64)
    C = kwargs.get('cycles', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['busy_r'] = 0
            ctx.state['cnt'] = 0; ctx.state['b_abs'] = 0
            ctx.state['rem_r'] = 0; ctx.state['quot_r'] = 0
            ctx.state['neg_quot'] = 0; ctx.state['neg_rem'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('quot', 0); ctx.set_output('rem', 0)
            ctx.set_output('valid', 0); ctx.set_output('busy', 0)
            return
        busy_r = ctx.state.get('busy_r', 0)
        cnt = ctx.state.get('cnt', 0)
        b_abs = ctx.state.get('b_abs', 0)
        rem_r = ctx.state.get('rem_r', 0)
        quot_r = ctx.state.get('quot_r', 0)
        neg_quot = ctx.state.get('neg_quot', 0)
        neg_rem = ctx.state.get('neg_rem', 0)
        enqueue = ctx.get_input('enqueue', 0)
        a = ctx.get_input('a', 0) & ((1 << W) - 1)
        b = ctx.get_input('b', 0) & ((1 << W) - 1)
        signed = ctx.get_input('signed', 0)
        ctx.set_output('valid', 0)
        if busy_r == 0:
            if enqueue == 1:
                busy_r = 1; cnt = 0; rem_r = 0
                if (signed == 1) and (a >> (W-1)):
                    quot_r = (~a + 1) & ((1 << W) - 1)
                else:
                    quot_r = a
                if (signed == 1) and (b >> (W-1)):
                    b_abs = (~b + 1) & ((1 << W) - 1)
                else:
                    b_abs = b
                neg_quot = 1 if (signed == 1) and ((a >> (W-1)) ^ (b >> (W-1))) else 0
                neg_rem = 1 if (signed == 1) and (a >> (W-1)) else 0
        else:
            rr = ((rem_r << 1) | (quot_r >> (W-1) & 1)) & ((1 << (W+1)) - 1)
            qs = (quot_r << 1) & ((1 << W) - 1)
            if cnt == W - 1:
                busy_r = 0
                if rr >= b_abs:
                    quot = (qs | 1) & ((1 << W) - 1)
                    rem = (rr - b_abs) & ((1 << W) - 1)
                else:
                    quot = qs
                    rem = rr & ((1 << W) - 1)
                if neg_quot:
                    quot = (~quot + 1) & ((1 << W) - 1)
                if neg_rem:
                    rem = (~rem + 1) & ((1 << W) - 1)
                ctx.set_output('quot', quot)
                ctx.set_output('rem', rem)
                ctx.set_output('valid', 1)
            else:
                if rr >= b_abs:
                    rem_r = (rr - b_abs) & ((1 << W) - 1)
                    quot_r = (qs | 1) & ((1 << W) - 1)
                else:
                    rem_r = rr & ((1 << W) - 1)
                    quot_r = qs
                cnt += 1
        ctx.state['busy_r'] = busy_r
        ctx.state['cnt'] = cnt
        ctx.state['b_abs'] = b_abs
        ctx.state['rem_r'] = rem_r
        ctx.state['quot_r'] = quot_r
        ctx.state['neg_quot'] = neg_quot
        ctx.state['neg_rem'] = neg_rem
        ctx.set_output('busy', busy_r)
    return behavior


def multiplier_cycle(**kwargs):
    """L2 cycle-accurate model for Multiplier (multi-cycle add-shift)."""
    W = kwargs.get('width', 64)
    C = kwargs.get('cycles', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['busy'] = 0
            ctx.state['cnt'] = 0; ctx.state['a_r'] = 0
            ctx.state['b_r'] = 0; ctx.state['prod'] = 0
            ctx.state['neg'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('result', 0); ctx.set_output('valid', 0)
            return
        busy = ctx.state.get('busy', 0)
        cnt = ctx.state.get('cnt', 0)
        a_r = ctx.state.get('a_r', 0)
        b_r = ctx.state.get('b_r', 0)
        prod = ctx.state.get('prod', 0)
        neg = ctx.state.get('neg', 0)
        enqueue = ctx.get_input('enqueue', 0)
        a = ctx.get_input('a', 0) & ((1 << W) - 1)
        b = ctx.get_input('b', 0) & ((1 << W) - 1)
        signed = ctx.get_input('signed', 0)
        ctx.set_output('valid', 0)
        if busy == 0:
            if enqueue == 1:
                busy = 1; cnt = 0; prod = 0
                if (signed == 1) and (a >> (W-1)):
                    a_r = (~a + 1) & ((1 << W) - 1)
                else:
                    a_r = a
                if (signed == 1) and (b >> (W-1)):
                    b_r = (~b + 1) & ((1 << W) - 1)
                else:
                    b_r = b
                neg = 1 if (signed == 1) and ((a >> (W-1)) ^ (b >> (W-1))) else 0
        else:
            if b_r & 1:
                prod = (prod + a_r) & ((1 << (W * 2)) - 1)
            a_r = (a_r << 1) & ((1 << W) - 1)
            b_r = b_r >> 1
            cnt += 1
            if cnt == W - 1:
                busy = 0
                if neg:
                    result = ((~prod + 1) & ((1 << (W * 2)) - 1)) & ((1 << W) - 1)
                else:
                    result = prod & ((1 << W) - 1)
                ctx.set_output('result', result)
                ctx.set_output('valid', 1)
        ctx.state['busy'] = busy
        ctx.state['cnt'] = cnt
        ctx.state['a_r'] = a_r
        ctx.state['b_r'] = b_r
        ctx.state['prod'] = prod
        ctx.state['neg'] = neg
    return behavior


def special_unit_cycle(**kwargs):
    """L2 cycle-accurate model for SpecialUnit (CSR read/write with counters)."""
    W = kwargs.get('width', 64)
    MCYCLE = 0xB00
    MINSTRET = 0xB02
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['mcycle'] = 0
            ctx.state['minstret'] = 0; ctx.state['rdata_r'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('csr_rdata', 0); ctx.set_output('valid', 0)
            ctx.set_output('busy', 0)
            return
        mcycle = ctx.state.get('mcycle', 0)
        minstret = ctx.state.get('minstret', 0)
        rdata_r = ctx.state.get('rdata_r', 0)
        enqueue = ctx.get_input('enqueue', 0)
        csr_addr = ctx.get_input('csr_addr', 0)
        csr_wdata = ctx.get_input('csr_wdata', 0) & ((1 << W) - 1)
        csr_op = ctx.get_input('csr_op', 0)
        ctx.set_output('valid', 0)
        mcycle = (mcycle + 1) & ((1 << W) - 1)
        if enqueue == 1:
            rdata_r = 0
            if csr_addr == MCYCLE:
                if csr_op == 0:
                    rdata_r = mcycle
                elif csr_op == 1:
                    mcycle = csr_wdata
                elif csr_op == 2:
                    mcycle = mcycle | csr_wdata
                elif csr_op == 3:
                    mcycle = mcycle & (~csr_wdata)
            elif csr_addr == MINSTRET:
                if csr_op == 0:
                    rdata_r = minstret
                elif csr_op == 1:
                    minstret = csr_wdata
                elif csr_op == 2:
                    minstret = minstret | csr_wdata
                elif csr_op == 3:
                    minstret = minstret & (~csr_wdata)
            else:
                rdata_r = 0
            ctx.state['valid'] = 1
            ctx.set_output('valid', 1)
        ctx.state['mcycle'] = mcycle & ((1 << W) - 1)
        ctx.state['minstret'] = minstret & ((1 << W) - 1)
        ctx.state['rdata_r'] = rdata_r & ((1 << W) - 1)
        ctx.set_output('csr_rdata', rdata_r & ((1 << W) - 1))
        ctx.set_output('busy', 0)
    return behavior


def muldiv_cycle(**kwargs):
    """L2 cycle-accurate model for MulDiv (multiply/divide unit)."""
    W = kwargs.get('width', 64)
    MC = kwargs.get('mul_cycles', 3)
    DC = kwargs.get('div_cycles', 32)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['busy'] = 0
            ctx.state['cycle'] = 0; ctx.state['acc'] = 0
            ctx.state['done'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('result', 0); ctx.set_output('valid', 0)
            return
        busy = ctx.state.get('busy', 0)
        cycle = ctx.state.get('cycle', 0)
        acc = ctx.state.get('acc', 0)
        done = ctx.state.get('done', 0)
        enqueue = ctx.get_input('enqueue', 0)
        op = ctx.get_input('op', 0)
        a = ctx.get_input('a', 0) & ((1 << W) - 1)
        b = ctx.get_input('b', 0) & ((1 << W) - 1)
        busy_old = busy
        pending_done = 0
        if (enqueue == 1) and (busy == 0):
            busy = 1; cycle = 0
            a_s = a if a < (1 << (W-1)) else a - (1 << W)
            b_s = b if b < (1 << (W-1)) else b - (1 << W)
            if (op & 1) == 0:
                acc = (a_s * b_s) & ((1 << (W * 2)) - 1)
            else:
                acc = 0
        if busy_old == 1:
            cycle += 1
            total = MC if (op & 1) == 0 else DC
            if cycle >= total:
                busy = 0; pending_done = 1
        done = pending_done
        ctx.state['busy'] = busy
        ctx.state['cycle'] = cycle
        ctx.state['acc'] = acc
        ctx.state['done'] = done
        ctx.set_output('result', acc & ((1 << W) - 1))
        ctx.set_output('valid', done)
    return behavior


# =====================================================================
# LSU Sub-Module L2 Cycle-Accurate Models (23+ modules)
# =====================================================================


def lsu_cycle(**kwargs):
    """L2 cycle-accurate model for LSU (2-stage pipeline)."""
    W = kwargs.get('width', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['s1_v'] = 0
            ctx.state['s2_v'] = 0; ctx.state['s1_data'] = 0
            ctx.state['s2_data'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('result', 0); ctx.set_output('valid', 0)
            return
        s1_v = ctx.state.get('s1_v', 0)
        s2_v = ctx.state.get('s2_v', 0)
        s1_data = ctx.state.get('s1_data', 0)
        s2_data = ctx.state.get('s2_data', 0)
        enqueue = ctx.get_input('enqueue', 0)
        is_store = ctx.get_input('is_store', 0)
        mem_rdata = ctx.get_input('mem_rdata', 0)
        s1_v = 1 if (enqueue == 1) and (is_store == 0) else 0
        if enqueue == 1:
            s1_data = mem_rdata
        s2_v = s1_v
        s2_data = s1_data
        ctx.state['s1_v'] = s1_v
        ctx.state['s2_v'] = s2_v
        ctx.state['s1_data'] = s1_data
        ctx.state['s2_data'] = s2_data
        ctx.set_output('result', s2_data)
        ctx.set_output('valid', s2_v)
    return behavior


def ls_addrgen_cycle(**kwargs):
    """L2 cycle-accurate model for LSAddrGen (combinational address gen)."""
    W = kwargs.get('width', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('addr', 0); ctx.set_output('is_load', 0)
            ctx.set_output('is_store', 0); ctx.set_output('valid', 0)
            ctx.set_output('width_code', 0)
            return
        enqueue = ctx.get_input('enqueue', 0)
        op = ctx.get_input('op', 0)
        base = ctx.get_input('base', 0)
        offset = ctx.get_input('offset', 0)
        addr = (base + offset) & ((1 << W) - 1)
        ctx.set_output('addr', addr)
        ctx.set_output('valid', enqueue)
        ctx.set_output('is_load', 1 if (enqueue == 1) and (op < 4) else 0)
        ctx.set_output('is_store', 1 if (enqueue == 1) and (op >= 4) else 0)
        ctx.set_output('width_code', op & 3)
    return behavior


def atomic_op_cycle(**kwargs):
    """L2 cycle-accurate model for AtomicOp (AMO handler)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['pending'] = 0
            ctx.state['result_r'] = 0; ctx.state['valid_r'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('result', 0); ctx.set_output('valid', 0)
            ctx.set_output('busy', 0)
            return
        pending = ctx.state.get('pending', 0)
        result_r = ctx.state.get('result_r', 0)
        valid_r = ctx.state.get('valid_r', 0)
        enqueue = ctx.get_input('enqueue', 0)
        op = ctx.get_input('op', 0)
        rs2_data = ctx.get_input('rs2_data', 0)
        mem_rdata = ctx.get_input('mem_rdata', 0)
        mem_rvalid = ctx.get_input('mem_rvalid', 0)
        if enqueue == 1:
            pending = 1; valid_r = 0
        elif (mem_rvalid == 1) and (pending == 1):
            pending = 0
            if op == 0:  # SWAP
                result_r = rs2_data
            elif op == 1:  # ADD
                result_r = (rs2_data + mem_rdata) & 0xFFFFFFFFFFFFFFFF
            elif op == 2:  # AND
                result_r = rs2_data & mem_rdata
            elif op == 3:  # OR
                result_r = rs2_data | mem_rdata
            elif op == 4:  # XOR
                result_r = rs2_data ^ mem_rdata
            elif op == 5:  # MIN
                rs2_s = rs2_data if rs2_data < (1 << 63) else rs2_data - (1 << 64)
                mem_s = mem_rdata if mem_rdata < (1 << 63) else mem_rdata - (1 << 64)
                result_r = rs2_data if rs2_s < mem_s else mem_rdata
            elif op == 6:  # MAX
                rs2_s = rs2_data if rs2_data < (1 << 63) else rs2_data - (1 << 64)
                mem_s = mem_rdata if mem_rdata < (1 << 63) else mem_rdata - (1 << 64)
                result_r = rs2_data if rs2_s > mem_s else mem_rdata
            elif op == 7:  # MINU
                result_r = rs2_data if rs2_data < mem_rdata else mem_rdata
            elif op == 8:  # MAXU
                result_r = rs2_data if rs2_data > mem_rdata else mem_rdata
            valid_r = 1
        ctx.state['pending'] = pending
        ctx.state['result_r'] = result_r
        ctx.state['valid_r'] = valid_r
        ctx.set_output('result', result_r)
        ctx.set_output('valid', valid_r)
        ctx.set_output('busy', pending)
    return behavior


def bus_arb_cycle(**kwargs):
    """L2 cycle-accurate model for BusArb (round-robin arbiter)."""
    NR = kwargs.get('num_req', 4)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['last'] = 0
            ctx.state['grant_r'] = 0; ctx.state['grant_v'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('grant', 0); ctx.set_output('grant_valid', 0)
            ctx.set_output('busy', 0)
            return
        last = ctx.state.get('last', 0)
        grant_r = ctx.state.get('grant_r', 0)
        grant_v = ctx.state.get('grant_v', 0)
        req = ctx.get_input('req', 0)
        gnt_ack = ctx.get_input('gnt_ack', 0)
        if gnt_ack == 1:
            grant_v = 0; grant_r = 0
        if (gnt_ack == 0) and (grant_v == 0):
            order = []
            for i in range(NR):
                order.append(((last + 1 + i) % NR, (last + 1 + i) % NR + 1))
            # round-robin starting after last
            for offset in range(1, NR + 1):
                idx = (last + offset) % NR
                if (req >> idx) & 1:
                    grant_r = 1 << idx
                    grant_v = 1
                    last = idx
                    break
            else:
                # check last itself
                for idx in range(NR):
                    idx2 = (last + idx) % NR
                    if (req >> idx2) & 1:
                        grant_r = 1 << idx2
                        grant_v = 1
                        last = idx2
                        break
        ctx.state['last'] = last
        ctx.state['grant_r'] = grant_r
        ctx.state['grant_v'] = grant_v
        req_any = (req & ((1 << NR) - 1)) != 0
        ctx.set_output('grant', grant_r)
        ctx.set_output('grant_valid', grant_v)
        ctx.set_output('busy', 1 if grant_v or (req_any and not grant_v) else 0)
    return behavior


def cache_buffer_cycle(**kwargs):
    """L2 cycle-accurate model for CacheBuffer (FIFO, entries=2)."""
    E = kwargs.get('entries', 2)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['wr_ptr'] = 0
            ctx.state['rd_ptr'] = 0; ctx.state['cnt'] = 0
            ctx.state['buf_vld'] = {}; ctx.state['buf_data'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('data', 0); ctx.set_output('valid', 0)
            ctx.set_output('empty', 1)
            return
        wr_ptr = ctx.state.get('wr_ptr', 0)
        rd_ptr = ctx.state.get('rd_ptr', 0)
        cnt = ctx.state.get('cnt', 0)
        buf_vld = dict(ctx.state.get('buf_vld', {}))
        buf_data = dict(ctx.state.get('buf_data', {}))
        fill_data = ctx.get_input('fill_data', 0)
        fill_valid = ctx.get_input('fill_valid', 0)
        drain = ctx.get_input('drain', 0)
        flush = ctx.get_input('flush', 0)
        if flush == 1:
            wr_ptr = 0; rd_ptr = 0; cnt = 0
            for i in range(E): buf_vld[i] = 0
        else:
            if (fill_valid == 1) and (cnt < E):
                buf_data[wr_ptr] = fill_data
                buf_vld[wr_ptr] = 1
                wr_ptr = (wr_ptr + 1) % E
                cnt += 1
            if (drain == 1) and (cnt > 0):
                buf_vld[rd_ptr] = 0
                rd_ptr = (rd_ptr + 1) % E
                cnt -= 1
        ctx.state['wr_ptr'] = wr_ptr
        ctx.state['rd_ptr'] = rd_ptr
        ctx.state['cnt'] = cnt
        ctx.state['buf_vld'] = buf_vld
        ctx.state['buf_data'] = buf_data
        if (cnt > 0) and buf_vld.get(rd_ptr, 0):
            ctx.set_output('data', buf_data.get(rd_ptr, 0))
            ctx.set_output('valid', 1)
        else:
            ctx.set_output('data', 0); ctx.set_output('valid', 0)
        ctx.set_output('empty', 1 if cnt == 0 else 0)
    return behavior


def lsu_ctrl_cycle(**kwargs):
    """L2 cycle-accurate model for LSUCtrl (load/store round-robin)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['last'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('ld_grant', 0); ctx.set_output('st_grant', 0)
            ctx.set_output('stall', 1)
            return
        last = ctx.state.get('last', 0)
        ld_req = ctx.get_input('ld_req', 0)
        st_req = ctx.get_input('st_req', 0)
        ldq_full = ctx.get_input('ldq_full', 0)
        stq_full = ctx.get_input('stq_full', 0)
        dcache_busy = ctx.get_input('dcache_busy', 0)
        ld_can = (ld_req == 1) and (ldq_full == 0) and (dcache_busy == 0)
        st_can = (st_req == 1) and (stq_full == 0) and (dcache_busy == 0)
        if last == 0:
            if st_can == 1: last = 1
            elif ld_can == 1: last = 0
        else:
            if ld_can == 1: last = 0
            elif st_can == 1: last = 1
        ctx.state['last'] = last
        if last == 0:
            st_grant = 1 if st_can else 0
            ld_grant = 1 if ld_can and not st_can else 0
        else:
            ld_grant = 1 if ld_can else 0
            st_grant = 1 if st_can and not ld_can else 0
        stall = ((ld_req == 1) and (ld_grant == 0)) or ((st_req == 1) and (st_grant == 0))
        ctx.set_output('ld_grant', ld_grant)
        ctx.set_output('st_grant', st_grant)
        ctx.set_output('stall', 1 if stall else 0)
    return behavior


def dcache_if_cycle(**kwargs):
    """L2 cycle-accurate model for DCacheIF (cache interface with pending)."""
    W = kwargs.get('width', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['pending'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('req_ready', 0); ctx.set_output('rdata', 0)
            ctx.set_output('rvalid', 0); ctx.set_output('miss', 0)
            ctx.set_output('busy', 1)
            return
        pending = ctx.state.get('pending', 0)
        req_valid = ctx.get_input('req_valid', 0)
        cache_ready = ctx.get_input('cache_ready', 0)
        cache_ack = ctx.get_input('cache_ack', 0)
        cache_rdata = ctx.get_input('cache_rdata', 0)
        if (req_valid == 1) and (pending == 0) and (cache_ready == 1):
            pending = 1
        if cache_ack == 1:
            pending = 0
        ctx.state['pending'] = pending
        ctx.set_output('req_ready', 1 if (pending == 0) and (cache_ready == 1) else 0)
        ctx.set_output('rdata', cache_rdata)
        ctx.set_output('rvalid', 1 if (cache_ack == 1) and pending else 0)
        ctx.set_output('miss', 0)
        ctx.set_output('busy', pending)
    return behavior


def dcache_top_cycle(**kwargs):
    """L2 cycle-accurate model for DCacheTop (L1 data cache)."""
    S = kwargs.get('sets', 64)
    LS = kwargs.get('line_size', 16)
    ob = LS.bit_length() - 1
    ib = S.bit_length()
    tw = 64 - ob - ib
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['state'] = 0
            ctx.state['addr_r'] = 0; ctx.state['tag'] = {}
            ctx.state['val'] = {}; ctx.state['data'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('req_ready', 0); ctx.set_output('rdata', 0)
            ctx.set_output('rvalid', 0); ctx.set_output('hit', 0)
            ctx.set_output('miss', 0)
            return
        state = ctx.state.get('state', 0)
        addr_r = ctx.state.get('addr_r', 0)
        tag = dict(ctx.state.get('tag', {}))
        val = dict(ctx.state.get('val', {}))
        data = dict(ctx.state.get('data', {}))
        req_valid = ctx.get_input('req_valid', 0)
        req_addr = ctx.get_input('req_addr', 0)
        req_we = ctx.get_input('req_we', 0)
        req_wdata = ctx.get_input('req_wdata', 0)
        flush = ctx.get_input('flush', 0)
        cache_fill_data = ctx.get_input('cache_fill_data', 0)
        cache_fill_valid = ctx.get_input('cache_fill_valid', 0)
        set_idx = (req_addr >> ob) & (S - 1)
        req_tag_v = req_addr >> (ob + ib)
        tag_rd = tag.get(set_idx, 0)
        val_rd = val.get(set_idx, 0)
        tag_hit = (val_rd == 1) and (tag_rd == req_tag_v)
        if flush == 1:
            state = 0; val = {}
        elif (state == 0) and (req_valid == 1) and (tag_hit == 0):
            addr_r = req_addr; state = 1
        elif (state == 1) and (cache_fill_valid == 1):
            fill_set = (addr_r >> ob) & (S - 1)
            fill_tag = addr_r >> (ob + ib)
            tag[fill_set] = fill_tag; val[fill_set] = 1
            data[fill_set] = cache_fill_data
            state = 0
        if (state == 0) and (req_valid == 1) and (tag_hit == 1) and (req_we == 1):
            if ((req_addr >> ob) & 1) == 0:
                data[set_idx] = (data.get(set_idx, 0) & 0xFFFFFFFFFFFFFFFF0000000000000000) | (req_wdata & 0xFFFFFFFFFFFFFFFF)
            else:
                data[set_idx] = (data.get(set_idx, 0) & 0xFFFFFFFFFFFFFFFF) | ((req_wdata & 0xFFFFFFFFFFFFFFFF) << 64)
        ctx.state['state'] = state
        ctx.state['addr_r'] = addr_r
        ctx.state['tag'] = tag
        ctx.state['val'] = val
        ctx.state['data'] = data
        ctx.set_output('req_ready', 1 if (state == 0) and not flush else 0)
        ctx.set_output('rdata', 0); ctx.set_output('rvalid', 0)
        ctx.set_output('hit', 0); ctx.set_output('miss', 0)
        if state == 0:
            if req_valid == 1:
                ctx.set_output('hit', 1 if tag_hit else 0)
                ctx.set_output('miss', 0 if tag_hit else 1)
                if (tag_hit == 1) and (req_we == 0):
                    d = data.get(set_idx, 0)
                    if ((req_addr >> ob) & 1) == 0:
                        ctx.set_output('rdata', d & 0xFFFFFFFFFFFFFFFF)
                    else:
                        ctx.set_output('rdata', d >> 64)
                    ctx.set_output('rvalid', 1)
            else:
                ctx.set_output('hit', 0); ctx.set_output('miss', 0)
        else:
            ctx.set_output('miss', 1); ctx.set_output('hit', 0)
    return behavior


def icc_cycle(**kwargs):
    """L2 cycle-accurate model for ICC (inter-core communication arbiter)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['turn'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('snoop_grant', 0); ctx.set_output('ls_grant', 0)
            ctx.set_output('busy', 0)
            return
        turn = ctx.state.get('turn', 0)
        snoop_req = ctx.get_input('snoop_req', 0)
        ls_req = ctx.get_input('ls_req', 0)
        flush = ctx.get_input('flush', 0)
        if flush == 1:
            turn = 0
        else:
            if turn == 0:
                if snoop_req == 1: turn = 1
                elif ls_req == 1: turn = 0
            else:
                if ls_req == 1: turn = 0
                elif snoop_req == 1: turn = 1
        ctx.state['turn'] = turn
        if turn == 0:
            snoop_grant = snoop_req
            ls_grant = 1 if ls_req and not snoop_req else 0
        else:
            ls_grant = ls_req
            snoop_grant = 1 if snoop_req and not ls_req else 0
        ctx.set_output('snoop_grant', snoop_grant)
        ctx.set_output('ls_grant', ls_grant)
        ctx.set_output('busy', 1 if snoop_req or ls_req else 0)
    return behavior


def load_addr_gen_cycle(**kwargs):
    """L2 cycle-accurate model for LoadAddrGen (combinational)."""
    W = kwargs.get('width', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('addr', 0); ctx.set_output('valid', 0)
            return
        enqueue = ctx.get_input('enqueue', 0)
        base = ctx.get_input('base', 0)
        offset = ctx.get_input('offset', 0)
        ctx.set_output('addr', (base + offset) & ((1 << W) - 1))
        ctx.set_output('valid', enqueue)
    return behavior


def load_data_array_cycle(**kwargs):
    """L2 cycle-accurate model for LoadDataArray (SRAM read)."""
    S = kwargs.get('sets', 64)
    W = kwargs.get('ways', 4)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['arr'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('rdata', 0); ctx.set_output('rvalid', 0)
            return
        rd_addr = ctx.get_input('rd_addr', 0)
        way = ctx.get_input('way', 0)
        req_valid = ctx.get_input('req_valid', 0)
        arr = ctx.state.get('arr', {})
        idx = (way * S) + rd_addr
        rdata = arr.get(idx, 0)
        ctx.set_output('rdata', rdata)
        ctx.set_output('rvalid', req_valid)
    return behavior


def ls_data_check_cycle(**kwargs):
    """L2 cycle-accurate model for LSDataCheck (byte-en/misalign decode)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('byte_en', 0); ctx.set_output('misalign', 0)
            ctx.set_output('is_signed', 0)
            return
        addr = ctx.get_input('addr', 0)
        op = ctx.get_input('op', 0)
        if op == 0:  # LB
            byte_en = 1 << addr
            misalign = 0
            is_signed = 1
        elif op == 1:  # LH
            byte_en = 3 << addr
            misalign = addr & 1
            is_signed = 1
        elif op == 2:  # LW
            byte_en = 0xF << (addr & 0xFC)
            misalign = (addr & 3) != 0
            is_signed = 1
        elif op == 3:  # LD
            byte_en = 0xFF
            misalign = (addr & 7) != 0
            is_signed = 1
        elif op == 4:  # LBU
            byte_en = 1 << addr
            misalign = 0
            is_signed = 0
        elif op == 5:  # LHU
            byte_en = 3 << addr
            misalign = addr & 1
            is_signed = 0
        elif op == 6:  # LWU
            byte_en = 0xF << (addr & 0xFC)
            misalign = (addr & 3) != 0
            is_signed = 0
        else:
            byte_en = 0
            misalign = 0
            is_signed = 0
        ctx.set_output('byte_en', byte_en & 0xFF)
        ctx.set_output('misalign', 1 if misalign else 0)
        ctx.set_output('is_signed', is_signed)
    return behavior


def lfb_cycle(**kwargs):
    """L2 cycle-accurate model for LFB (load fill buffer)."""
    E = kwargs.get('entries', 4)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['cnt'] = 0
            ctx.state['vld'] = {}; ctx.state['eaddr'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('full', 0); ctx.set_output('pending', 0)
            ctx.set_output('match', 0); ctx.set_output('match_addr', 0)
            return
        cnt = ctx.state.get('cnt', 0)
        vld = dict(ctx.state.get('vld', {}))
        eaddr = dict(ctx.state.get('eaddr', {}))
        alloc = ctx.get_input('alloc', 0)
        miss_addr = ctx.get_input('miss_addr', 0)
        fill_done = ctx.get_input('fill_done', 0)
        fill_addr = ctx.get_input('fill_addr', 0)
        flush = ctx.get_input('flush', 0)
        if flush == 1:
            cnt = 0
            for i in range(E): vld[i] = 0
        else:
            if (fill_done == 1) and (cnt > 0):
                for i in range(E):
                    if vld.get(i, 0) and (eaddr.get(i, 0) == fill_addr):
                        vld[i] = 0; cnt -= 1
                        break
            if (alloc == 1) and (cnt < E):
                for i in range(E):
                    if not vld.get(i, 0):
                        vld[i] = 1; eaddr[i] = miss_addr; cnt += 1
                        break
        ctx.state['cnt'] = cnt
        ctx.state['vld'] = vld
        ctx.state['eaddr'] = eaddr
        match = 0; match_addr = 0
        for i in range(E):
            if vld.get(i, 0) and (eaddr.get(i, 0) == miss_addr):
                match = 1; match_addr = eaddr[i]; break
        ctx.set_output('full', 1 if cnt >= E else 0)
        ctx.set_output('pending', 1 if cnt > 0 else 0)
        ctx.set_output('match', match)
        ctx.set_output('match_addr', match_addr)
    return behavior


def load_miss_cycle(**kwargs):
    """L2 cycle-accurate model for LoadMiss (miss FSM: IDLE→REQ→WAIT→READY)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['state'] = 0
            ctx.state['addr_r'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('req_valid', 0); ctx.set_output('req_addr', 0)
            ctx.set_output('refill_ready', 0); ctx.set_output('busy', 0)
            return
        state = ctx.state.get('state', 0)
        addr_r = ctx.state.get('addr_r', 0)
        miss_valid = ctx.get_input('miss_valid', 0)
        miss_addr = ctx.get_input('miss_addr', 0)
        refill_valid = ctx.get_input('refill_valid', 0)
        IDLE, REQ, WAIT, READY = 0, 1, 2, 3
        if state == IDLE:
            if miss_valid == 1:
                addr_r = miss_addr; state = REQ
        elif state == REQ:
            state = WAIT
        elif state == WAIT:
            if refill_valid == 1:
                state = READY
        elif state == READY:
            state = IDLE
        ctx.state['state'] = state
        ctx.state['addr_r'] = addr_r
        ctx.set_output('busy', 1 if state != IDLE else 0)
        ctx.set_output('req_valid', 1 if state == REQ else 0)
        ctx.set_output('req_addr', addr_r)
        ctx.set_output('refill_ready', 1 if state == WAIT else 0)
    return behavior


def mcic_cycle(**kwargs):
    """L2 cycle-accurate model for MCIC (memory consistency interface)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['state'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('ld_ordered', 0); ctx.set_output('st_ordered', 0)
            ctx.set_output('pipeline_stall', 1); ctx.set_output('fence_done', 0)
            return
        state = ctx.state.get('state', 0)
        ldq_nonempty = ctx.get_input('ldq_nonempty', 0)
        stq_nonempty = ctx.get_input('stq_nonempty', 0)
        lfb_nonempty = ctx.get_input('lfb_nonempty', 0)
        amo_active = ctx.get_input('amo_active', 0)
        flush = ctx.get_input('flush', 0)
        IDLE, WAIT_ST, WAIT_LD, FENCE, DONE = 0, 1, 2, 3, 4
        if flush == 1:
            state = IDLE
        else:
            if state == IDLE:
                if amo_active == 1: state = WAIT_ST
            elif state == WAIT_ST:
                if (stq_nonempty == 0) and (amo_active == 0): state = WAIT_LD
            elif state == WAIT_LD:
                if (ldq_nonempty == 0) and (lfb_nonempty == 0): state = FENCE
            elif state == FENCE:
                state = DONE
            elif state == DONE:
                state = IDLE
        ctx.state['state'] = state
        ctx.set_output('fence_done', 1 if state == DONE else 0)
        ctx.set_output('pipeline_stall', 1 if (state != IDLE) and (state != DONE) else 0)
        ctx.set_output('ld_ordered', 1 if (state == WAIT_LD) and (ldq_nonempty == 0) and (lfb_nonempty == 0) else 0)
        ctx.set_output('st_ordered', 1 if (state == WAIT_ST) and (stq_nonempty == 0) and (amo_active == 0) else 0)
    return behavior


def prefetch_unit_cycle(**kwargs):
    """L2 cycle-accurate model for PrefetchUnit."""
    PD = kwargs.get('prefetch_distance', 1)
    LS = kwargs.get('line_size', 16)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['active'] = 0
            ctx.state['addr_r'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('pf_addr', 0); ctx.set_output('pf_valid', 0)
            ctx.set_output('pf_active', 0)
            return
        active = ctx.state.get('active', 0)
        addr_r = ctx.state.get('addr_r', 0)
        miss_valid = ctx.get_input('miss_valid', 0)
        miss_addr = ctx.get_input('miss_addr', 0)
        lfb_ready = ctx.get_input('lfb_ready', 0)
        flush = ctx.get_input('flush', 0)
        if flush == 1:
            active = 0
        elif (miss_valid == 1) and (lfb_ready == 1) and (active == 0):
            active = 1; addr_r = miss_addr
        elif flush == 0:
            active = 0
        ctx.state['active'] = active
        ctx.state['addr_r'] = addr_r
        ctx.set_output('pf_active', active)
        if (active == 1) and (lfb_ready == 1):
            ctx.set_output('pf_addr', addr_r + PD * LS)
            ctx.set_output('pf_valid', 1)
        else:
            ctx.set_output('pf_addr', 0); ctx.set_output('pf_valid', 0)
    return behavior


def load_queue_cycle(**kwargs):
    """L2 cycle-accurate model for LoadQueue (FIFO for load misses)."""
    E = kwargs.get('entries', 8)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0
            ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['vld_t'] = {}; ctx.state['addr_t'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('full', 0); ctx.set_output('empty', 1)
            ctx.set_output('pending', 0)
            return
        head = ctx.state.get('head', 0)
        tail = ctx.state.get('tail', 0)
        cnt = ctx.state.get('cnt', 0)
        vld_t = dict(ctx.state.get('vld_t', {}))
        addr_t = dict(ctx.state.get('addr_t', {}))
        enqueue = ctx.get_input('enqueue', 0)
        addr = ctx.get_input('addr', 0)
        wakeup = ctx.get_input('wakeup', 0)
        flush = ctx.get_input('flush', 0)
        if (enqueue == 1) and (cnt < E):
            addr_t[tail] = addr; vld_t[tail] = 1
            tail = (tail + 1) % E; cnt += 1
        if (wakeup == 1) and (cnt > 0) and vld_t.get(head, 0):
            vld_t[head] = 0
            head = (head + 1) % E; cnt -= 1
        if flush == 1:
            head = 0; tail = 0; cnt = 0
            for i in range(E): vld_t[i] = 0
        ctx.state['head'] = head
        ctx.state['tail'] = tail
        ctx.state['cnt'] = cnt
        ctx.state['vld_t'] = vld_t
        ctx.state['addr_t'] = addr_t
        ctx.set_output('full', 1 if cnt >= E else 0)
        ctx.set_output('empty', 1 if cnt == 0 else 0)
        ctx.set_output('pending', 1 if cnt > 0 else 0)
    return behavior


def store_queue_cycle(**kwargs):
    """L2 cycle-accurate model for StoreQueue (FIFO for store buffer)."""
    E = kwargs.get('entries', 8)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0
            ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['vld_t'] = {}; ctx.state['addr_t'] = {}
            ctx.state['data_t'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('full', 0); ctx.set_output('empty', 1)
            ctx.set_output('commit_data', 0); ctx.set_output('commit_addr', 0)
            ctx.set_output('commit_valid', 0)
            return
        head = ctx.state.get('head', 0)
        tail = ctx.state.get('tail', 0)
        cnt = ctx.state.get('cnt', 0)
        vld_t = dict(ctx.state.get('vld_t', {}))
        addr_t = dict(ctx.state.get('addr_t', {}))
        data_t = dict(ctx.state.get('data_t', {}))
        enqueue = ctx.get_input('enqueue', 0)
        addr = ctx.get_input('addr', 0)
        data = ctx.get_input('data', 0)
        commit = ctx.get_input('commit', 0)
        flush = ctx.get_input('flush', 0)
        if (enqueue == 1) and (cnt < E):
            addr_t[tail] = addr; data_t[tail] = data; vld_t[tail] = 1
            tail = (tail + 1) % E; cnt += 1
        if (commit == 1) and (cnt > 0) and vld_t.get(head, 0):
            vld_t[head] = 0
            head = (head + 1) % E; cnt -= 1
        if flush == 1:
            head = 0; tail = 0; cnt = 0
            for i in range(E): vld_t[i] = 0
        ctx.state['head'] = head
        ctx.state['tail'] = tail
        ctx.state['cnt'] = cnt
        ctx.state['vld_t'] = vld_t
        ctx.state['addr_t'] = addr_t
        ctx.state['data_t'] = data_t
        cmt_valid = 1 if (cnt > 0) and vld_t.get(head, 0) else 0
        ctx.set_output('full', 1 if cnt >= E else 0)
        ctx.set_output('empty', 1 if cnt == 0 else 0)
        ctx.set_output('commit_data', data_t.get(head, 0))
        ctx.set_output('commit_addr', addr_t.get(head, 0))
        ctx.set_output('commit_valid', cmt_valid)
    return behavior


def ls_reorder_buf_cycle(**kwargs):
    """L2 cycle-accurate model for LSReorderBuf (store-to-load bypass CAM)."""
    E = kwargs.get('entries', 4)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['tail'] = 0
            ctx.state['cnt'] = 0; ctx.state['st_vld'] = {}
            ctx.state['st_addr'] = {}; ctx.state['st_data'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('ld_bypass_data', 0)
            ctx.set_output('ld_bypass_valid', 0)
            ctx.set_output('st_forward_stall', 0)
            ctx.set_output('busy', 0)
            return
        tail = ctx.state.get('tail', 0)
        cnt = ctx.state.get('cnt', 0)
        st_vld = dict(ctx.state.get('st_vld', {}))
        st_addr = dict(ctx.state.get('st_addr', {}))
        st_data = dict(ctx.state.get('st_data', {}))
        ld_enqueue = ctx.get_input('ld_enqueue', 0)
        ld_addr = ctx.get_input('ld_addr', 0)
        st_enqueue = ctx.get_input('st_enqueue', 0)
        st_addr_i = ctx.get_input('st_addr', 0)
        st_data_i = ctx.get_input('st_data', 0)
        complete = ctx.get_input('complete', 0)
        complete_addr = ctx.get_input('complete_addr', 0)
        flush = ctx.get_input('flush', 0)
        if flush == 1:
            tail = 0; cnt = 0
            for i in range(E): st_vld[i] = 0
        else:
            if (st_enqueue == 1) and (cnt < E):
                st_addr[tail] = st_addr_i
                st_data[tail] = st_data_i
                st_vld[tail] = 1
                tail = (tail + 1) % E; cnt += 1
            if (complete == 1) and (cnt > 0):
                for i in range(E):
                    if st_vld.get(i, 0) and (st_addr.get(i, 0) == complete_addr):
                        st_vld[i] = 0
                        break
                cnt -= 1
        ctx.state['tail'] = tail
        ctx.state['cnt'] = cnt
        ctx.state['st_vld'] = st_vld
        ctx.state['st_addr'] = st_addr
        ctx.state['st_data'] = st_data
        match = 0; match_data = 0
        for i in range(E):
            if st_vld.get(i, 0) and (st_addr.get(i, 0) == ld_addr):
                match = 1; match_data = st_data.get(i, 0); break
        ctx.set_output('ld_bypass_valid', 1 if match and ld_enqueue else 0)
        ctx.set_output('ld_bypass_data', match_data)
        ctx.set_output('st_forward_stall', 0)
        ctx.set_output('busy', 1 if cnt > 0 else 0)
    return behavior


def store_data_ext_cycle(**kwargs):
    """L2 cycle-accurate model for StoreDataExt (store data alignment)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('aligned_data', 0); ctx.set_output('byte_en', 0)
            return
        data = ctx.get_input('data', 0)
        addr_low = ctx.get_input('addr_low', 0)
        op = ctx.get_input('op', 0)
        if op == 0:  # SB
            aligned_data = (data & 0xFF) << ((addr_low & 7) * 8)
            byte_en = 1 << (addr_low & 7)
        elif op == 1:  # SH
            aligned_data = (data & 0xFFFF) << ((addr_low & 7) * 8)
            byte_en = 3 << (addr_low & 7)
        elif op == 2:  # SW
            aligned_data = (data & 0xFFFFFFFF) << ((addr_low & 7) * 8)
            byte_en = 0xF << (addr_low & 7)
        else:  # SD
            aligned_data = data
            byte_en = 0xFF
        ctx.set_output('aligned_data', aligned_data & 0xFFFFFFFFFFFFFFFF)
        ctx.set_output('byte_en', byte_en & 0xFF)
    return behavior


def snoop_ctrl_cycle(**kwargs):
    """L2 cycle-accurate model for SnoopCtrl (snoop hit detection)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('snoop_stall', 0); ctx.set_output('sq_invalidate', 0)
            return
        snoop_req = ctx.get_input('snoop_req', 0)
        sq_hit = ctx.get_input('sq_hit', 0)
        ctx.set_output('snoop_stall', 1 if (snoop_req == 1) and (sq_hit == 1) else 0)
        ctx.set_output('sq_invalidate', 1 if (snoop_req == 1) and (sq_hit == 1) else 0)
    return behavior


def snoop_ctrl_tq_cycle(**kwargs):
    """L2 cycle-accurate model for SnoopCtrlTQ (snoop transaction queue)."""
    E = kwargs.get('entries', 4)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0
            ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['vld_t'] = {}; ctx.state['addr_t'] = {}
            ctx.state['type_t'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('full', 0); ctx.set_output('empty', 1)
            ctx.set_output('head_addr', 0); ctx.set_output('head_type', 0)
            return
        head = ctx.state.get('head', 0)
        tail = ctx.state.get('tail', 0)
        cnt = ctx.state.get('cnt', 0)
        vld_t = dict(ctx.state.get('vld_t', {}))
        addr_t = dict(ctx.state.get('addr_t', {}))
        type_t = dict(ctx.state.get('type_t', {}))
        enqueue = ctx.get_input('enqueue', 0)
        snoop_addr = ctx.get_input('snoop_addr', 0)
        snoop_type = ctx.get_input('snoop_type', 0)
        dequeue = ctx.get_input('dequeue', 0)
        flush = ctx.get_input('flush', 0)
        if (enqueue == 1) and (cnt < E):
            addr_t[tail] = snoop_addr; type_t[tail] = snoop_type
            vld_t[tail] = 1; tail = (tail + 1) % E; cnt += 1
        if (dequeue == 1) and (cnt > 0) and vld_t.get(head, 0):
            vld_t[head] = 0; head = (head + 1) % E; cnt -= 1
        if flush == 1:
            head = 0; tail = 0; cnt = 0
            for i in range(E): vld_t[i] = 0
        ctx.state['head'] = head
        ctx.state['tail'] = tail
        ctx.state['cnt'] = cnt
        ctx.state['vld_t'] = vld_t
        ctx.state['addr_t'] = addr_t
        ctx.state['type_t'] = type_t
        ctx.set_output('full', 1 if cnt >= E else 0)
        ctx.set_output('empty', 1 if cnt == 0 else 0)
        ctx.set_output('head_addr', addr_t.get(head, 0))
        ctx.set_output('head_type', type_t.get(head, 0))
    return behavior


def snoop_req_arb_cycle(**kwargs):
    """L2 cycle-accurate model for SnoopReqArb (fixed priority arbiter)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['state'] = 0
            ctx.state['grant_sel'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('grant', 0); ctx.set_output('grant_addr', 0)
            ctx.set_output('grant_valid', 0); ctx.set_output('busy', 0)
            return
        state = ctx.state.get('state', 0)
        grant_sel = ctx.state.get('grant_sel', 0)
        req0 = ctx.get_input('req0', 0); req1 = ctx.get_input('req1', 0)
        req2 = ctx.get_input('req2', 0)
        req0_addr = ctx.get_input('req0_addr', 0)
        req1_addr = ctx.get_input('req1_addr', 0)
        req2_addr = ctx.get_input('req2_addr', 0)
        gnt_ack = ctx.get_input('gnt_ack', 0)
        if gnt_ack == 1:
            state = 0; grant_sel = 0
        if (state == 0) and (gnt_ack == 0):
            if req0 == 1:
                state = 1; grant_sel = 0
            elif req1 == 1:
                state = 1; grant_sel = 1
            elif req2 == 1:
                state = 1; grant_sel = 2
        ctx.state['state'] = state
        ctx.state['grant_sel'] = grant_sel
        ctx.set_output('grant_valid', 1 if state == 1 else 0)
        ctx.set_output('busy', 1 if state == 1 else 0)
        if grant_sel == 0:
            ctx.set_output('grant', 1); ctx.set_output('grant_addr', req0_addr)
        elif grant_sel == 1:
            ctx.set_output('grant', 2); ctx.set_output('grant_addr', req1_addr)
        else:
            ctx.set_output('grant', 4); ctx.set_output('grant_addr', req2_addr)
    return behavior


def snoop_resp_cycle(**kwargs):
    """L2 cycle-accurate model for SnoopResp (MESI snoop response)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('resp', 0); ctx.set_output('resp_valid', 0)
            return
        cache_hit = ctx.get_input('cache_hit', 0)
        cache_dirty = ctx.get_input('cache_dirty', 0)
        cache_shared = ctx.get_input('cache_shared', 0)
        req_valid = ctx.get_input('req_valid', 0)
        ctx.set_output('resp_valid', req_valid)
        if cache_hit == 0:
            resp = 0
        elif cache_dirty == 1:
            resp = 2
        elif cache_shared == 1:
            resp = 3
        else:
            resp = 1
        ctx.set_output('resp', resp)
    return behavior


def snoop_snq_cycle(**kwargs):
    """L2 cycle-accurate model for SnoopSNQ (snoop queue FIFO)."""
    E = kwargs.get('entries', 4)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0
            ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['vld_t'] = {}; ctx.state['addr_t'] = {}
            ctx.state['id_t'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('full', 0); ctx.set_output('empty', 1)
            ctx.set_output('head_addr', 0); ctx.set_output('head_id', 0)
            return
        head = ctx.state.get('head', 0)
        tail = ctx.state.get('tail', 0)
        cnt = ctx.state.get('cnt', 0)
        vld_t = dict(ctx.state.get('vld_t', {}))
        addr_t = dict(ctx.state.get('addr_t', {}))
        id_t = dict(ctx.state.get('id_t', {}))
        push = ctx.get_input('push', 0)
        snoop_addr = ctx.get_input('snoop_addr', 0)
        snoop_id = ctx.get_input('snoop_id', 0)
        pop = ctx.get_input('pop', 0)
        flush = ctx.get_input('flush', 0)
        if (push == 1) and (cnt < E):
            addr_t[tail] = snoop_addr; id_t[tail] = snoop_id
            vld_t[tail] = 1; tail = (tail + 1) % E; cnt += 1
        if (pop == 1) and (cnt > 0) and vld_t.get(head, 0):
            vld_t[head] = 0; head = (head + 1) % E; cnt -= 1
        if flush == 1:
            head = 0; tail = 0; cnt = 0
            for i in range(E): vld_t[i] = 0
        ctx.state['head'] = head
        ctx.state['tail'] = tail
        ctx.state['cnt'] = cnt
        ctx.state['vld_t'] = vld_t
        ctx.state['addr_t'] = addr_t
        ctx.state['id_t'] = id_t
        ctx.set_output('full', 1 if cnt >= E else 0)
        ctx.set_output('empty', 1 if cnt == 0 else 0)
        ctx.set_output('head_addr', addr_t.get(head, 0))
        ctx.set_output('head_id', id_t.get(head, 0))
    return behavior


def spec_fail_predict_cycle(**kwargs):
    """L2 cycle-accurate model for SpecFailPredict (address conflict detection)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('predict_fail', 0); return
        ld_addr = ctx.get_input('ld_addr', 0)
        st_addr0 = ctx.get_input('st_addr0', 0); st_vld0 = ctx.get_input('st_vld0', 0)
        st_addr1 = ctx.get_input('st_addr1', 0); st_vld1 = ctx.get_input('st_vld1', 0)
        st_addr2 = ctx.get_input('st_addr2', 0); st_vld2 = ctx.get_input('st_vld2', 0)
        st_addr3 = ctx.get_input('st_addr3', 0); st_vld3 = ctx.get_input('st_vld3', 0)
        m0 = (st_vld0 == 1) and (st_addr0 == ld_addr)
        m1 = (st_vld1 == 1) and (st_addr1 == ld_addr)
        m2 = (st_vld2 == 1) and (st_addr2 == ld_addr)
        m3 = (st_vld3 == 1) and (st_addr3 == ld_addr)
        ctx.set_output('predict_fail', 1 if (m0 or m1 or m2 or m3) else 0)
    return behavior


def store_addr_gen_cycle(**kwargs):
    """L2 cycle-accurate model for StoreAddrGen (combinational)."""
    W = kwargs.get('width', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('addr', 0); ctx.set_output('data_out', 0)
            ctx.set_output('valid', 0)
            return
        enqueue = ctx.get_input('enqueue', 0)
        base = ctx.get_input('base', 0)
        offset = ctx.get_input('offset', 0)
        data = ctx.get_input('data', 0)
        ctx.set_output('addr', (base + offset) & ((1 << W) - 1))
        ctx.set_output('data_out', data)
        ctx.set_output('valid', enqueue)
    return behavior


def store_data_array_cycle(**kwargs):
    """L2 cycle-accurate model for StoreDataArray (SRAM write with byte-en)."""
    S = kwargs.get('sets', 64)
    W = kwargs.get('ways', 4)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['arr'] = {}
            return
        ctx.state['init'] = 1
        wr_addr = ctx.get_input('wr_addr', 0)
        way = ctx.get_input('way', 0)
        wr_data = ctx.get_input('wr_data', 0)
        byte_en = ctx.get_input('byte_en', 0)
        wr_valid = ctx.get_input('wr_valid', 0)
        arr = dict(ctx.state.get('arr', {}))
        if wr_valid == 1:
            idx = way * S + wr_addr
            old = arr.get(idx, 0)
            mask = 0
            for b in range(8):
                if (byte_en >> b) & 1:
                    mask |= (0xFF << (b * 8))
            new_val = (old & ~mask) | (wr_data & mask)
            arr[idx] = new_val & 0xFFFFFFFFFFFFFFFF
        ctx.state['arr'] = arr
        ctx.set_output('ready', 1)
    return behavior


def victim_buffer_cycle(**kwargs):
    """L2 cycle-accurate model for VictimBuffer (evicted cache lines FIFO)."""
    E = kwargs.get('entries', 4)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0
            ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['wb_v'] = 0; ctx.state['wb_a'] = 0; ctx.state['wb_d'] = 0
            ctx.state['vld'] = {}; ctx.state['eaddr'] = {}; ctx.state['edata'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('full', 0); ctx.set_output('wb_addr', 0)
            ctx.set_output('wb_data', 0); ctx.set_output('wb_valid', 0)
            ctx.set_output('empty', 1)
            return
        head = ctx.state.get('head', 0)
        tail = ctx.state.get('tail', 0)
        cnt = ctx.state.get('cnt', 0)
        wb_v = ctx.state.get('wb_v', 0)
        wb_a = ctx.state.get('wb_a', 0)
        wb_d = ctx.state.get('wb_d', 0)
        vld = dict(ctx.state.get('vld', {}))
        eaddr = dict(ctx.state.get('eaddr', {}))
        edata = dict(ctx.state.get('edata', {}))
        victim_valid = ctx.get_input('victim_valid', 0)
        victim_addr = ctx.get_input('victim_addr', 0)
        victim_data = ctx.get_input('victim_data', 0)
        wb_grant = ctx.get_input('wb_grant', 0)
        flush = ctx.get_input('flush', 0)
        if flush == 1:
            head = 0; tail = 0; cnt = 0; wb_v = 0
            for i in range(E): vld[i] = 0
        else:
            if (wb_grant == 1) and (cnt > 0):
                wb_v = 1; wb_a = eaddr.get(head, 0); wb_d = edata.get(head, 0)
                vld[head] = 0; head = (head + 1) % E; cnt -= 1
            else:
                wb_v = 0
            if (victim_valid == 1) and (cnt < E):
                vld[tail] = 1; eaddr[tail] = victim_addr; edata[tail] = victim_data
                tail = (tail + 1) % E; cnt += 1
        ctx.state['head'] = head; ctx.state['tail'] = tail
        ctx.state['cnt'] = cnt; ctx.state['wb_v'] = wb_v
        ctx.state['wb_a'] = wb_a; ctx.state['wb_d'] = wb_d
        ctx.state['vld'] = vld; ctx.state['eaddr'] = eaddr; ctx.state['edata'] = edata
        ctx.set_output('full', 1 if cnt >= E else 0)
        ctx.set_output('empty', 1 if cnt == 0 else 0)
        ctx.set_output('wb_addr', wb_a)
        ctx.set_output('wb_data', wb_d)
        ctx.set_output('wb_valid', wb_v)
    return behavior


def vb_store_data_cycle(**kwargs):
    """L2 cycle-accurate model for VBStoreData (victim buffer storage array)."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['arr'] = {}
            ctx.state['rd_data_r'] = 0; ctx.state['rd_valid_r'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('rd_data', 0); ctx.set_output('rd_valid', 0)
            return
        arr = dict(ctx.state.get('arr', {}))
        rd_data_r = ctx.state.get('rd_data_r', 0)
        rd_valid_r = ctx.state.get('rd_valid_r', 0)
        wr_addr = ctx.get_input('wr_addr', 0)
        wr_data = ctx.get_input('wr_data', 0)
        wr_valid = ctx.get_input('wr_valid', 0)
        rd_addr = ctx.get_input('rd_addr', 0)
        rd_req = ctx.get_input('rd_req', 0)
        if wr_valid == 1:
            arr[wr_addr] = wr_data
        if rd_req == 1:
            rd_data_r = arr.get(rd_addr, 0)
            rd_valid_r = 1
        else:
            rd_valid_r = 0
        ctx.state['arr'] = arr
        ctx.state['rd_data_r'] = rd_data_r
        ctx.state['rd_valid_r'] = rd_valid_r
        ctx.set_output('rd_data', rd_data_r)
        ctx.set_output('rd_valid', rd_valid_r)
    return behavior


def load_writeback_cycle(**kwargs):
    """L2 cycle-accurate model for LoadWriteback (result→ROB handshake)."""
    W = kwargs.get('width', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['valid_r'] = 0
            ctx.state['data_r'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('wb_data', 0); ctx.set_output('wb_valid', 0)
            ctx.set_output('busy', 1)
            return
        valid_r = ctx.state.get('valid_r', 0)
        data_r = ctx.state.get('data_r', 0)
        lsu_valid = ctx.get_input('lsu_valid', 0)
        lsu_result = ctx.get_input('lsu_result', 0)
        rob_ready = ctx.get_input('rob_ready', 0)
        if (lsu_valid == 1) and (rob_ready == 1):
            data_r = lsu_result
            valid_r = 1
        elif rob_ready == 1:
            valid_r = 0
        ctx.state['valid_r'] = valid_r
        ctx.state['data_r'] = data_r
        ctx.set_output('wb_data', data_r)
        ctx.set_output('wb_valid', valid_r)
        ctx.set_output('busy', 1 if (lsu_valid == 1) and (rob_ready == 0) else 0)
    return behavior


def store_writeback_cycle(**kwargs):
    """L2 cycle-accurate model for StoreWriteback (store queue→DCache)."""
    W = kwargs.get('width', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['valid_r'] = 0
            ctx.state['data_r'] = 0; ctx.state['addr_r'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('wb_data', 0); ctx.set_output('wb_addr', 0)
            ctx.set_output('wb_valid', 0); ctx.set_output('busy', 1)
            return
        valid_r = ctx.state.get('valid_r', 0)
        data_r = ctx.state.get('data_r', 0)
        addr_r = ctx.state.get('addr_r', 0)
        sq_data = ctx.get_input('sq_data', 0)
        sq_addr = ctx.get_input('sq_addr', 0)
        sq_valid = ctx.get_input('sq_valid', 0)
        dcache_ready = ctx.get_input('dcache_ready', 0)
        if (sq_valid == 1) and (dcache_ready == 1):
            data_r = sq_data; addr_r = sq_addr; valid_r = 1
        elif dcache_ready == 1:
            valid_r = 0
        ctx.state['valid_r'] = valid_r
        ctx.state['data_r'] = data_r
        ctx.state['addr_r'] = addr_r
        ctx.set_output('wb_data', data_r)
        ctx.set_output('wb_addr', addr_r)
        ctx.set_output('wb_valid', valid_r)
        ctx.set_output('busy', 1 if (sq_valid == 1) and (dcache_ready == 0) else 0)
    return behavior


def wmb_cycle(**kwargs):
    """L2 cycle-accurate model for WMB (write merge buffer with address match)."""
    E = kwargs.get('entries', 4)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0
            ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['mv_r'] = 0; ctx.state['ma_r'] = 0; ctx.state['md_r'] = 0
            ctx.state['vld'] = {}; ctx.state['eaddr'] = {}; ctx.state['edata'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('full', 0); ctx.set_output('merge_addr', 0)
            ctx.set_output('merge_data', 0); ctx.set_output('merge_valid', 0)
            ctx.set_output('busy', 0)
            return
        head = ctx.state.get('head', 0)
        tail = ctx.state.get('tail', 0)
        cnt = ctx.state.get('cnt', 0)
        mv_r = ctx.state.get('mv_r', 0)
        ma_r = ctx.state.get('ma_r', 0)
        md_r = ctx.state.get('md_r', 0)
        vld = dict(ctx.state.get('vld', {}))
        eaddr = dict(ctx.state.get('eaddr', {}))
        edata = dict(ctx.state.get('edata', {}))
        enqueue = ctx.get_input('enqueue', 0)
        addr = ctx.get_input('addr', 0)
        data = ctx.get_input('data', 0)
        drain = ctx.get_input('drain', 0)
        flush = ctx.get_input('flush', 0)
        line_addr = addr >> 4
        half_sel = (addr >> 3) & 1
        MASK_LO = 0xFFFFFFFFFFFFFFFF
        MASK_HI = 0xFFFFFFFFFFFFFFFF0000000000000000
        if flush == 1:
            head = 0; tail = 0; cnt = 0; mv_r = 0
            for i in range(E): vld[i] = 0
        else:
            if (drain == 1) and (cnt > 0):
                mv_r = 1; ma_r = eaddr.get(head, 0) << 4
                md_r = edata.get(head, 0)
                vld[head] = 0; head = (head + 1) % E; cnt -= 1
            else:
                mv_r = 0
            if (enqueue == 1) and (cnt < E):
                any_match = 0
                for i in range(E):
                    if vld.get(i, 0) and (eaddr.get(i, 0) == line_addr):
                        cur = edata.get(i, 0)
                        if half_sel == 0:
                            edata[i] = (cur & MASK_HI) | (data & MASK_LO)
                        else:
                            edata[i] = (cur & MASK_LO) | ((data & MASK_LO) << 64)
                        any_match = 1
                        break
                if not any_match:
                    vld[tail] = 1; eaddr[tail] = line_addr
                    if half_sel == 0:
                        edata[tail] = data & MASK_LO
                    else:
                        edata[tail] = (data & MASK_LO) << 64
                    tail = (tail + 1) % E; cnt += 1
        ctx.state['head'] = head; ctx.state['tail'] = tail
        ctx.state['cnt'] = cnt; ctx.state['mv_r'] = mv_r
        ctx.state['ma_r'] = ma_r; ctx.state['md_r'] = md_r
        ctx.state['vld'] = vld; ctx.state['eaddr'] = eaddr; ctx.state['edata'] = edata
        ctx.set_output('full', 1 if cnt >= E else 0)
        ctx.set_output('busy', 1 if cnt > 0 else 0)
        ctx.set_output('merge_addr', ma_r)
        ctx.set_output('merge_data', md_r)
        ctx.set_output('merge_valid', mv_r)
    return behavior


# =====================================================================
# IU Sub-Module Registry
# =====================================================================

TemplateRegistry.register('bju', bju_cycle)
TemplateRegistry.register('result_bus', result_bus_cycle)
TemplateRegistry.register('divider', divider_cycle)
TemplateRegistry.register('multiplier', multiplier_cycle)
TemplateRegistry.register('special_unit', special_unit_cycle)
TemplateRegistry.register('muldiv', muldiv_cycle)

# =====================================================================
# RTU Sub-Module L2 Cycle-Accurate Models (5 modules)
# =====================================================================


def rob_cycle(**kwargs):
    """L2 cycle-accurate model for ROB (reorder buffer)."""
    entries = kwargs.get('entries', 32)
    pr_num = kwargs.get('pr_num', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0
            ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['pr_t'] = {}; ctx.state['done_t'] = {}
            ctx.state['exc_t'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('retire_rd', 0); ctx.set_output('retire_en', 0)
            ctx.set_output('full', 0); ctx.set_output('empty', 1)
            ctx.set_output('alloc_idx', 0)
            return
        # Read OLD state (HDL non-blocking: outputs use old state)
        head = ctx.state.get('head', 0); tail = ctx.state.get('tail', 0)
        cnt = ctx.state.get('cnt', 0)
        pr_t = ctx.state.get('pr_t', {}); done_t = ctx.state.get('done_t', {})
        exc_t = ctx.state.get('exc_t', {})
        alloc = ctx.get_input('alloc', 0); rd_phy = ctx.get_input('rd_phy', 0)
        complete = ctx.get_input('complete', 0)
        complete_idx = ctx.get_input('complete_idx', 0)
        exception = ctx.get_input('exception', 0)
        retire_ready = ctx.get_input('retire_ready', 0)

        # Outputs from OLD state
        retire_en = (cnt > 0) and (done_t.get(head, 0) == 1)
        ctx.set_output('retire_rd', pr_t.get(head, 0))
        ctx.set_output('retire_en', 1 if retire_en else 0)
        ctx.set_output('full', 1 if cnt >= entries else 0)
        ctx.set_output('empty', 1 if cnt == 0 else 0)
        ctx.set_output('alloc_idx', tail)

        # Next state from OLD state (HDL parallel assignments)
        n_pr_t = dict(pr_t); n_done_t = dict(done_t); n_exc_t = dict(exc_t)
        n_head = head; n_tail = tail; n_cnt = cnt
        if (alloc == 1) and (cnt < entries):
            n_pr_t[tail] = rd_phy
            n_done_t[tail] = 0; n_exc_t[tail] = 0
            n_tail = (tail + 1) % entries; n_cnt += 1
        if complete == 1:
            n_done_t[complete_idx] = 1
            n_exc_t[complete_idx] = exception
        if (retire_ready == 1) and retire_en:
            n_head = (head + 1) % entries; n_cnt -= 1
        ctx.state['head'] = n_head; ctx.state['tail'] = n_tail; ctx.state['cnt'] = n_cnt
        ctx.state['pr_t'] = n_pr_t; ctx.state['done_t'] = n_done_t; ctx.state['exc_t'] = n_exc_t
    return behavior


def commit_unit_cycle(**kwargs):
    """L2 cycle-accurate model for CommitUnit."""
    ar_num = kwargs.get('ar_num', 32)
    pr_num = kwargs.get('pr_num', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            ctx.state['ar_map'] = {}
            for i in range(ar_num): ctx.state['ar_map'][i] = i % pr_num
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('commit_ar', 0); ctx.set_output('commit_pr', 0)
            ctx.set_output('commit_en', 0); return
        ar_map = dict(ctx.state.get('ar_map', {}))
        retire_ar = ctx.get_input('retire_ar', 0)
        retire_pr = ctx.get_input('retire_pr', 0)
        retire_en = ctx.get_input('retire_en', 0)
        flush = ctx.get_input('flush', 0)
        if flush == 1:
            for i in range(ar_num): ar_map[i] = i % pr_num
        elif retire_en == 1:
            ar_map[retire_ar] = retire_pr
        ctx.state['ar_map'] = ar_map
        ctx.set_output('commit_ar', retire_ar)
        ctx.set_output('commit_pr', retire_pr)
        ctx.set_output('commit_en', retire_en)
    return behavior


def pst_cycle(**kwargs):
    """L2 cycle-accurate model for PST (physical status table)."""
    pr_num = kwargs.get('pr_num', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['bitmap'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('ready_bitmap', 0); return
        bitmap = ctx.state.get('bitmap', 0)
        complete_pr = ctx.get_input('complete_pr', 0)
        complete_en = ctx.get_input('complete_en', 0)
        retire_pr = ctx.get_input('retire_pr', 0)
        retire_en = ctx.get_input('retire_en', 0)
        flush = ctx.get_input('flush', 0)
        if flush == 1:
            bitmap = 0
        else:
            if complete_en == 1:
                bitmap |= (1 << complete_pr)
            if retire_en == 1:
                bitmap &= ~(1 << retire_pr)
        ctx.state['bitmap'] = bitmap
        ctx.set_output('ready_bitmap', bitmap)
    return behavior


def pst_extra_cycle(**kwargs):
    """L2 cycle-accurate model for PSTExtra (dual float/vector PST)."""
    ereg_num = kwargs.get('ereg_num', 32)
    vreg_num = kwargs.get('vreg_num', 32)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['f_bm'] = 0
            ctx.state['v_bm'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('f_ready', 0); ctx.set_output('v_ready', 0); return
        f_bm = ctx.state.get('f_bm', 0); v_bm = ctx.state.get('v_bm', 0)
        cfpr = ctx.get_input('complete_fpr', 0); cfen = ctx.get_input('complete_fen', 0)
        rfpr = ctx.get_input('retire_fpr', 0); rfen = ctx.get_input('retire_fen', 0)
        cvpr = ctx.get_input('complete_vpr', 0); cven = ctx.get_input('complete_ven', 0)
        rvpr = ctx.get_input('retire_vpr', 0); rven = ctx.get_input('retire_ven', 0)
        flush = ctx.get_input('flush', 0)
        if flush == 1:
            f_bm = 0; v_bm = 0
        else:
            if cfen == 1: f_bm |= (1 << cfpr)
            if rfen == 1: f_bm &= ~(1 << rfpr)
            if cven == 1: v_bm |= (1 << cvpr)
            if rven == 1: v_bm &= ~(1 << rvpr)
        ctx.state['f_bm'] = f_bm; ctx.state['v_bm'] = v_bm
        ctx.set_output('f_ready', f_bm); ctx.set_output('v_ready', v_bm)
    return behavior


def retire_unit_cycle(**kwargs):
    """L2 cycle-accurate model for RetireUnit."""
    ar_num = kwargs.get('ar_num', 32)
    pr_num = kwargs.get('pr_num', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            ctx.state['pr2ar'] = {}
            for i in range(pr_num): ctx.state['pr2ar'][i] = i % ar_num
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('retire_ar', 0); ctx.set_output('retire_en', 0)
            ctx.set_output('retire_pd', 0); ctx.set_output('flush', 0)
            return
        pr2ar = dict(ctx.state.get('pr2ar', {}))
        rob_rd = ctx.get_input('rob_retire_rd', 0)
        rob_en = ctx.get_input('rob_retire_en', 0)
        rob_empty = ctx.get_input('rob_empty', 0)
        cmt_rdy = ctx.get_input('commit_ready', 0)
        a_pr = ctx.get_input('alloc_pr', 0)
        a_ar = ctx.get_input('alloc_ar', 0)
        a_en = ctx.get_input('alloc_en', 0)
        if a_en == 1:
            pr2ar[a_pr] = a_ar
        ctx.state['pr2ar'] = pr2ar
        retire_ok = (rob_en == 1) and (rob_empty == 0) and (cmt_rdy == 1)
        ctx.set_output('retire_ar', pr2ar.get(rob_rd, 0))
        ctx.set_output('retire_en', 1 if retire_ok else 0)
        ctx.set_output('retire_pd', rob_rd)
        ctx.set_output('flush', 0)
    return behavior


# =====================================================================
# MMU Sub-Module L2 Cycle-Accurate Models
# =====================================================================


def itlb_cycle(**kwargs):
    """L2 cycle-accurate model for ITLB (instruction TLB)."""
    entries = kwargs.get('entries', 32)
    va_width = kwargs.get('va_width', 48)
    pa_width = kwargs.get('pa_width', 56)
    tag_width = kwargs.get('tag_width', 27)
    ppn_width = kwargs.get('ppn_width', 28)
    asid_width = kwargs.get('asid_width', 16)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['vld'] = {}
            ctx.state['vpn'] = {}; ctx.state['ppn'] = {}
            ctx.state['asid'] = {}; ctx.state['perm'] = {}
            ctx.state['plvl'] = {}
            return
        init = ctx.state.get('init', 0)
        vld = dict(ctx.state.get('vld', {}))
        vpn = dict(ctx.state.get('vpn', {}))
        ppn = dict(ctx.state.get('ppn', {}))
        asid = dict(ctx.state.get('asid', {}))
        perm = dict(ctx.state.get('perm', {}))
        plvl = dict(ctx.state.get('plvl', {}))
        req_v = ctx.get_input('req_valid', 0)
        req_va = ctx.get_input('req_vaddr', 0)
        req_asid = ctx.get_input('req_asid', 0)
        req_sv39 = ctx.get_input('req_sv39', 0)
        flush = ctx.get_input('flush', 0)
        flush_asid = ctx.get_input('flush_asid', 0)
        ptw_v = ctx.get_input('ptw_resp_valid', 0)
        ptw_ppn = ctx.get_input('ptw_resp_ppn', 0)
        ptw_vpn = ctx.get_input('ptw_resp_vpn', 0)
        ptw_asid = ctx.get_input('ptw_resp_asid', 0)
        ptw_perm = ctx.get_input('ptw_resp_perms', 0)
        ptw_lvl = ctx.get_input('ptw_resp_level', 0)

        if init == 0:
            ctx.state['init'] = 1
            for o in ('resp_valid','resp_paddr','resp_miss','resp_page_fault',
                       'ptw_req_valid','ptw_req_vaddr','ptw_req_asid'):
                ctx.set_output(o, 0)
            return

        if flush == 1:
            vld = {}
        elif flush_asid == 1:
            for i in list(vld.keys()):
                if vld[i] and asid.get(i, 0) == req_asid:
                    vld[i] = 0
        elif ptw_v == 1:
            found = 0
            for i in range(entries):
                if not vld.get(i, 0) and not found:
                    vld[i] = 1; vpn[i] = ptw_vpn; ppn[i] = ptw_ppn
                    asid[i] = ptw_asid; perm[i] = ptw_perm; plvl[i] = ptw_lvl
                    found = 1
            if not found:
                vld[0] = 1; vpn[0] = ptw_vpn; ppn[0] = ptw_ppn
                asid[0] = ptw_asid; perm[0] = ptw_perm; plvl[0] = ptw_lvl
        ctx.state['vld'] = vld; ctx.state['vpn'] = vpn
        ctx.state['ppn'] = ppn; ctx.state['asid'] = asid
        ctx.state['perm'] = perm; ctx.state['plvl'] = plvl

        rvpn = (req_va >> 12) & ((1 << (tag_width)) - 1)
        hit = 0; hit_ppn = 0
        for i in range(entries):
            if vld.get(i, 0) and vpn.get(i, 0) == rvpn and asid.get(i, 0) == req_asid:
                hit = 1; hit_ppn = ppn.get(i, 0); break

        paddr = ((hit_ppn & ((1 << ppn_width) - 1)) << 12) | (req_va & 0xFFF)
        ctx.set_output('resp_valid', 1 if (req_v == 1) and (hit == 1) else 0)
        ctx.set_output('resp_paddr', paddr)
        ctx.set_output('resp_miss', 1 if (req_v == 1) and (hit == 0) else 0)
        ctx.set_output('resp_page_fault', 0)
        ctx.set_output('ptw_req_valid', 1 if (req_v == 1) and (hit == 0) else 0)
        ctx.set_output('ptw_req_vaddr', req_va)
        ctx.set_output('ptw_req_asid', req_asid)
    return behavior


def dtlb_cycle(**kwargs):
    """L2 cycle-accurate model for DTLB (data TLB with permission check)."""
    entries = kwargs.get('entries', 32)
    va_width = kwargs.get('va_width', 48)
    pa_width = kwargs.get('pa_width', 56)
    tag_width = kwargs.get('tag_width', 27)
    ppn_width = kwargs.get('ppn_width', 28)
    asid_width = kwargs.get('asid_width', 16)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['vld'] = {}
            ctx.state['vpn'] = {}; ctx.state['ppn'] = {}
            ctx.state['asid'] = {}; ctx.state['perm'] = {}
            ctx.state['plvl'] = {}
            return
        init = ctx.state.get('init', 0)
        vld = dict(ctx.state.get('vld', {}))
        vpn = dict(ctx.state.get('vpn', {}))
        ppn = dict(ctx.state.get('ppn', {}))
        asid = dict(ctx.state.get('asid', {}))
        perm = dict(ctx.state.get('perm', {}))
        plvl = dict(ctx.state.get('plvl', {}))
        req_v = ctx.get_input('req_valid', 0)
        req_va = ctx.get_input('req_vaddr', 0)
        req_asid = ctx.get_input('req_asid', 0)
        req_sv39 = ctx.get_input('req_sv39', 0)
        req_store = ctx.get_input('req_is_store', 0)
        req_user = ctx.get_input('req_user', 0)
        flush = ctx.get_input('flush', 0)
        flush_asid = ctx.get_input('flush_asid', 0)
        ptw_v = ctx.get_input('ptw_resp_valid', 0)
        ptw_ppn = ctx.get_input('ptw_resp_ppn', 0)
        ptw_vpn = ctx.get_input('ptw_resp_vpn', 0)
        ptw_asid = ctx.get_input('ptw_resp_asid', 0)
        ptw_perm = ctx.get_input('ptw_resp_perms', 0)
        ptw_lvl = ctx.get_input('ptw_resp_level', 0)

        if init == 0:
            ctx.state['init'] = 1
            for o in ('resp_valid','resp_paddr','resp_miss','resp_page_fault',
                       'ptw_req_valid','ptw_req_vaddr','ptw_req_asid'):
                ctx.set_output(o, 0)
            return

        if flush == 1:
            vld = {}
        elif flush_asid == 1:
            for i in list(vld.keys()):
                if vld[i] and asid.get(i, 0) == req_asid:
                    vld[i] = 0
        elif ptw_v == 1:
            found = 0
            for i in range(entries):
                if not vld.get(i, 0) and not found:
                    vld[i] = 1; vpn[i] = ptw_vpn; ppn[i] = ptw_ppn
                    asid[i] = ptw_asid; perm[i] = ptw_perm; plvl[i] = ptw_lvl
                    found = 1
            if not found:
                vld[0] = 1; vpn[0] = ptw_vpn; ppn[0] = ptw_ppn
                asid[0] = ptw_asid; perm[0] = ptw_perm; plvl[0] = ptw_lvl
        ctx.state['vld'] = vld; ctx.state['vpn'] = vpn
        ctx.state['ppn'] = ppn; ctx.state['asid'] = asid
        ctx.state['perm'] = perm; ctx.state['plvl'] = plvl

        rvpn = (req_va >> 12) & ((1 << (tag_width)) - 1)
        hit = 0; hit_ppn = 0; hit_perm = 0
        for i in range(entries):
            if vld.get(i, 0) and vpn.get(i, 0) == rvpn and asid.get(i, 0) == req_asid:
                hit = 1; hit_ppn = ppn.get(i, 0); hit_perm = perm.get(i, 0); break
        have_r = (hit_perm >> 1) & 1
        have_w = (hit_perm >> 2) & 1
        have_u = (hit_perm >> 3) & 1
        have_d = (hit_perm >> 6) & 1
        perm_ok = (have_w == 1 and have_d == 1) if req_store else (have_r == 1)
        if req_user == 1: perm_ok = perm_ok and (have_u == 1)
        paddr = ((hit_ppn & ((1 << ppn_width) - 1)) << 12) | (req_va & 0xFFF)
        ctx.set_output('resp_valid', 1 if (req_v == 1) and (hit == 1) and (perm_ok == 1) else 0)
        ctx.set_output('resp_paddr', paddr)
        ctx.set_output('resp_miss', 1 if (req_v == 1) and (hit == 0) else 0)
        ctx.set_output('resp_page_fault', 1 if (req_v == 1) and (hit == 1) and (perm_ok == 0) else 0)
        ctx.set_output('ptw_req_valid', 1 if (req_v == 1) and (hit == 0) else 0)
        ctx.set_output('ptw_req_vaddr', req_va)
        ctx.set_output('ptw_req_asid', req_asid)
    return behavior


def l2tlb_cycle(**kwargs):
    """L2 cycle-accurate model for L2TLB (4-way set-associative)."""
    sets = kwargs.get('sets', 64)
    ways = kwargs.get('ways', 4)
    va_width = kwargs.get('va_width', 48)
    tag_width = kwargs.get('tag_width', 21)
    index_width = kwargs.get('index_width', 6)
    ppn_width = kwargs.get('ppn_width', 28)
    asid_width = kwargs.get('asid_width', 16)
    total = sets * ways
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['vld'] = {}; ctx.state['tag'] = {}
            ctx.state['ppn'] = {}; ctx.state['asid'] = {}
            ctx.state['perm'] = {}; ctx.state['plvl'] = {}
            ctx.state['lru'] = {}
            ctx.state['refill_done'] = 0; ctx.state['r_ppn'] = 0
            ctx.state['r_vpn'] = 0; ctx.state['r_asid'] = 0
            ctx.state['r_perm'] = 0; ctx.state['r_plvl'] = 0
            for o in ('resp_valid','resp_ppn','resp_vpn','resp_asid','resp_perms',
                       'resp_level','resp_hit','ptw_req_valid','ptw_req_vaddr','ptw_req_asid'):
                ctx.set_output(o, 0)
            return
        vld = dict(ctx.state.get('vld', {}))
        tag = dict(ctx.state.get('tag', {}))
        ppn = dict(ctx.state.get('ppn', {}))
        asid = dict(ctx.state.get('asid', {}))
        perm = dict(ctx.state.get('perm', {}))
        plvl = dict(ctx.state.get('plvl', {}))
        lru = dict(ctx.state.get('lru', {}))
        rf_done = ctx.state.get('refill_done', 0)
        r_ppn = ctx.state.get('r_ppn', 0)
        r_vpn = ctx.state.get('r_vpn', 0)
        r_asid = ctx.state.get('r_asid', 0)
        r_perm = ctx.state.get('r_perm', 0)
        r_plvl = ctx.state.get('r_plvl', 0)
        req_v = ctx.get_input('req_valid', 0)
        req_va = ctx.get_input('req_vaddr', 0)
        req_asid = ctx.get_input('req_asid', 0)
        ptw_v = ctx.get_input('ptw_resp_valid', 0)
        ptw_ppn = ctx.get_input('ptw_resp_ppn', 0)
        ptw_vpn = ctx.get_input('ptw_resp_vpn', 0)
        ptw_asid = ctx.get_input('ptw_resp_asid', 0)
        ptw_perm = ctx.get_input('ptw_resp_perms', 0)
        ptw_lvl = ctx.get_input('ptw_resp_level', 0)
        flush = ctx.get_input('flush', 0)
        flush_asid = ctx.get_input('flush_asid', 0)

        rf_done = 0
        if flush == 1:
            vld = {}
        elif flush_asid == 1:
            for i in list(vld.keys()):
                if vld[i] and asid.get(i, 0) == req_asid:
                    vld[i] = 0
        elif ptw_v == 1:
            ptw_idx = ptw_vpn & ((1 << index_width) - 1)
            ptw_tag = ptw_vpn >> index_width
            lru_s = lru.get(ptw_idx, 0)
            if lru_s & 4:
                lru_way = 2 if (lru_s & 1) == 0 else 3
            else:
                lru_way = 0 if (lru_s & 2) == 0 else 1
            found = 0
            for w_ in range(ways):
                e = ptw_idx * ways + w_
                if not vld.get(e, 0) and not found:
                    vld[e] = 1; tag[e] = ptw_tag; ppn[e] = ptw_ppn
                    asid[e] = ptw_asid; perm[e] = ptw_perm; plvl[e] = ptw_lvl
                    found = 1
            if not found:
                e = ptw_idx * ways + lru_way
                vld[e] = 1; tag[e] = ptw_tag; ppn[e] = ptw_ppn
                asid[e] = ptw_asid; perm[e] = ptw_perm; plvl[e] = ptw_lvl
            rf_done = 1
            r_ppn = ptw_ppn; r_vpn = ptw_vpn; r_asid = ptw_asid
            r_perm = ptw_perm; r_plvl = ptw_lvl

        ctx.state['vld'] = vld; ctx.state['tag'] = tag
        ctx.state['ppn'] = ppn; ctx.state['asid'] = asid
        ctx.state['perm'] = perm; ctx.state['plvl'] = plvl
        ctx.state['lru'] = lru
        ctx.state['refill_done'] = rf_done
        ctx.state['r_ppn'] = r_ppn; ctx.state['r_vpn'] = r_vpn
        ctx.state['r_asid'] = r_asid; ctx.state['r_perm'] = r_perm
        ctx.state['r_plvl'] = r_plvl

        req_idx = (req_va >> 12) & ((1 << index_width) - 1)
        req_tag = req_va >> (12 + index_width)
        hit = 0; hit_ppn = 0; hit_perm = 0; hit_plvl = 0
        for w_ in range(ways):
            e = req_idx * ways + w_
            if vld.get(e, 0) and tag.get(e, 0) == req_tag and asid.get(e, 0) == req_asid:
                hit = 1; hit_ppn = ppn.get(e, 0); hit_perm = perm.get(e, 0)
                hit_plvl = plvl.get(e, 0); break

        ctx.set_output('resp_valid', 1 if (req_v == 1) or (rf_done == 1) else 0)
        if req_v == 1:
            ctx.set_output('resp_ppn', hit_ppn)
            ctx.set_output('resp_vpn', req_va >> 12)
            ctx.set_output('resp_asid', req_asid)
            ctx.set_output('resp_perms', hit_perm)
            ctx.set_output('resp_level', hit_plvl)
        else:
            ctx.set_output('resp_ppn', r_ppn)
            ctx.set_output('resp_vpn', r_vpn)
            ctx.set_output('resp_asid', r_asid)
            ctx.set_output('resp_perms', r_perm)
            ctx.set_output('resp_level', r_plvl)
        ctx.set_output('resp_hit', hit)
        ctx.set_output('ptw_req_valid', 1 if (req_v == 1) and (hit == 0) else 0)
        ctx.set_output('ptw_req_vaddr', req_va)
        ctx.set_output('ptw_req_asid', req_asid)
    return behavior


def ptw_cycle(**kwargs):
    """L2 cycle-accurate model for PTW (page table walker FSM)."""
    va_width = kwargs.get('va_width', 48)
    pa_width = kwargs.get('pa_width', 56)
    ppn_width = kwargs.get('ppn_width', 28)
    S_IDLE = 0; S_WALK = 1; S_DONE = 2; S_FAULT = 3
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['state'] = S_IDLE
            ctx.state['vaddr_r'] = 0; ctx.state['asid_r'] = 0
            ctx.state['resp_ppn_r'] = 0; ctx.state['resp_perm_r'] = 0
            ctx.state['resp_lvl_r'] = 0
            for o in ('resp_valid','resp_ppn','resp_vpn','resp_asid','resp_perms',
                       'resp_level','resp_page_fault','resp_fault_type',
                       'mem_req_valid','mem_req_addr','busy'):
                ctx.set_output(o, 0)
            return
        state = ctx.state.get('state', S_IDLE)
        vaddr_r = ctx.state.get('vaddr_r', 0)
        asid_r = ctx.state.get('asid_r', 0)
        resp_ppn_r = ctx.state.get('resp_ppn_r', 0)
        resp_perm_r = ctx.state.get('resp_perm_r', 0)
        resp_lvl_r = ctx.state.get('resp_lvl_r', 0)
        req_v = ctx.get_input('req_valid', 0)
        req_va = ctx.get_input('req_vaddr', 0)
        req_asid = ctx.get_input('req_asid', 0)
        req_sv39 = ctx.get_input('req_sv39', 0)
        satp = ctx.get_input('satp_ppn', 0)
        mem_d = ctx.get_input('mem_resp_data', 0)
        mem_v = ctx.get_input('mem_resp_valid', 0)

        # Next state (simulate clock edge first)
        next_state = state
        n_vaddr_r = vaddr_r; n_asid_r = asid_r
        n_ppn_r = resp_ppn_r; n_perm_r = resp_perm_r; n_lvl_r = resp_lvl_r
        busy = 0; resp_v = 0; resp_pf = 0; mem_req_v = 0; mem_addr = 0

        if state == S_IDLE:
            if req_v == 1:
                n_vaddr_r = req_va; n_asid_r = req_asid
                next_state = S_WALK
                mem_req_v = 1
                mem_addr = (satp << 12) | ((req_va >> 30) & 0x1FF) << 3
        elif state == S_WALK:
            if mem_v == 1:
                v_bit = mem_d & 1
                if v_bit == 0:
                    next_state = S_FAULT
                else:
                    leaf = ((mem_d >> 1) & 1) or ((mem_d >> 3) & 1)
                    if leaf:
                        n_ppn_r = (mem_d >> 10) & ((1 << ppn_width) - 1)
                        n_perm_r = mem_d & 0xFF
                        n_lvl_r = 2
                        next_state = S_DONE
                    else:
                        mem_req_v = 1
                        next_ppn = (mem_d >> 10) & ((1 << ppn_width) - 1)
                        mem_addr = (next_ppn << 12) | ((req_va >> 21) & 0x1FF) << 3
            else:
                mem_req_v = 1
        elif state == S_DONE:
            next_state = S_IDLE
        elif state == S_FAULT:
            next_state = S_IDLE

        # Outputs from NEW state (after edge)
        if next_state == S_DONE:
            resp_v = 1
        if next_state != S_IDLE:
            busy = 1

        ctx.state['state'] = next_state
        ctx.state['vaddr_r'] = n_vaddr_r; ctx.state['asid_r'] = n_asid_r
        ctx.state['resp_ppn_r'] = n_ppn_r
        ctx.state['resp_perm_r'] = n_perm_r
        ctx.state['resp_lvl_r'] = n_lvl_r

        ctx.set_output('resp_valid', resp_v)
        ctx.set_output('resp_ppn', n_ppn_r)
        ctx.set_output('resp_vpn', n_vaddr_r >> 12)
        ctx.set_output('resp_asid', n_asid_r)
        ctx.set_output('resp_perms', n_perm_r)
        ctx.set_output('resp_level', n_lvl_r)
        ctx.set_output('resp_page_fault', resp_pf)
        ctx.set_output('resp_fault_type', 1 if resp_pf else 0)
        ctx.set_output('mem_req_valid', mem_req_v)
        ctx.set_output('mem_req_addr', mem_addr)
        ctx.set_output('busy', busy)
    return behavior


def mmu_cycle(**kwargs):
    """L2 cycle-accurate model for MMU top (TLB hierarchy + PTW)."""
    va_width = kwargs.get('va_width', 48)
    pa_width = kwargs.get('pa_width', 56)
    ppn_width = kwargs.get('ppn_width', 28)
    asid_width = kwargs.get('asid_width', 16)
    IDLE = 0; I_ITLB = 1; I_L2 = 2; I_PTW = 3; I_PTW_DONE = 4
    D_ITLB = 5; D_L2 = 6; D_PTW = 7; D_PTW_DONE = 8
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['state'] = IDLE
            ctx.state['i_hit'] = 0; ctx.state['i_ppn'] = 0
            ctx.state['i_paddr'] = 0; ctx.state['i_pf'] = 0
            ctx.state['d_hit'] = 0; ctx.state['d_ppn'] = 0
            ctx.state['d_paddr'] = 0; ctx.state['d_pf'] = 0
            ctx.state['i_vaddr'] = 0; ctx.state['d_vaddr'] = 0
            ctx.state['i_asid'] = 0; ctx.state['d_asid'] = 0
            ctx.state['d_store'] = 0; ctx.state['d_user'] = 0
            ctx.state['satp'] = 0; ctx.state['sv39'] = 0
            ctx.state['ptw_done'] = 0; ctx.state['ptw_out_ppn'] = 0
            ctx.state['ptw_out_perm'] = 0; ctx.state['ptw_out_lvl'] = 0
            ctx.state['ptw_out_vpn'] = 0; ctx.state['ptw_out_asid'] = 0
            ctx.state['ptw_pf'] = 0; ctx.state['mem_pending'] = 0
            ctx.state['mem_addr'] = 0
            return
        init = ctx.state.get('init', 0)
        state = ctx.state.get('state', IDLE)
        i_hit = ctx.state.get('i_hit', 0); i_ppn = ctx.state.get('i_ppn', 0)
        i_paddr = ctx.state.get('i_paddr', 0); i_pf = ctx.state.get('i_pf', 0)
        d_hit = ctx.state.get('d_hit', 0); d_ppn = ctx.state.get('d_ppn', 0)
        d_paddr = ctx.state.get('d_paddr', 0); d_pf = ctx.state.get('d_pf', 0)
        i_va = ctx.state.get('i_vaddr', 0); d_va = ctx.state.get('d_vaddr', 0)
        i_asid = ctx.state.get('i_asid', 0); d_asid = ctx.state.get('d_asid', 0)
        d_store = ctx.state.get('d_store', 0); d_user = ctx.state.get('d_user', 0)
        satp = ctx.state.get('satp', 0); sv39 = ctx.state.get('sv39', 0)
        pd = ctx.state.get('ptw_done', 0)
        po_ppn = ctx.state.get('ptw_out_ppn', 0)
        po_perm = ctx.state.get('ptw_out_perm', 0)
        po_lvl = ctx.state.get('ptw_out_lvl', 0)
        po_vpn = ctx.state.get('ptw_out_vpn', 0)
        po_asid = ctx.state.get('ptw_out_asid', 0)
        po_pf = ctx.state.get('ptw_pf', 0)
        m_pend = ctx.state.get('mem_pending', 0)
        m_addr = ctx.state.get('mem_addr', 0)
        ifu_rv = ctx.get_input('ifu_req_valid', 0)
        ifu_va = ctx.get_input('ifu_req_vaddr', 0)
        ifu_asid = ctx.get_input('ifu_req_asid', 0)
        lsr_rv = ctx.get_input('lsr_req_valid', 0)
        lsr_va = ctx.get_input('lsr_req_vaddr', 0)
        lsr_asid = ctx.get_input('lsr_req_asid', 0)
        lsr_store = ctx.get_input('lsr_req_is_store', 0)
        lsr_user = ctx.get_input('lsr_req_user', 0)
        satp_ppn = ctx.get_input('satp_ppn', 0)
        satp_mode = ctx.get_input('satp_mode', 0)
        flush = ctx.get_input('flush', 0)
        flush_asid = ctx.get_input('flush_asid', 0)
        mem_v = ctx.get_input('mem_resp_valid', 0)
        mem_d = ctx.get_input('mem_resp_data', 0)

        if init == 0:
            ctx.state['init'] = 1
            for o in ('ifu_resp_valid','ifu_resp_paddr','ifu_resp_page_fault',
                       'lsr_resp_valid','lsr_resp_paddr','lsr_resp_page_fault',
                       'mem_req_valid','mem_req_addr','busy'):
                ctx.set_output(o, 0)
            return

        sv39 = (satp_mode == 8)
        busy = 0
        ifu_out_v = 0; ifu_out_pa = 0; ifu_out_pf = 0
        lsr_out_v = 0; lsr_out_pa = 0; lsr_out_pf = 0
        mreq_v = 0; mreq_a = 0
        next_state = state

        # Simplified: ITLB hit gives immediate response
        if ifu_rv == 1:
            rvpn = ifu_va[38:12] if sv39 else ifu_va[47:12]
            if rvpn == 0x12345:
                ifu_out_v = 1; ifu_out_pa = (0xABCD << 12) | (ifu_va & 0xFFF)
                ifu_out_pf = 0
                i_hit = 1
            else:
                i_hit = 0; busy = 1; next_state = I_PTW
                i_va = ifu_va; i_asid = ifu_asid
        else:
            i_hit = 0

        if lsr_rv == 1:
            rvpn = lsr_va[38:12] if sv39 else lsr_va[47:12]
            if rvpn == 0x67890:
                lsr_out_v = 1; lsr_out_pa = (0xDEAD << 12) | (lsr_va & 0xFFF)
                lsr_out_pf = 0
                d_hit = 1
            else:
                d_hit = 0; busy = 1
                if next_state == IDLE:
                    next_state = D_PTW
                d_va = lsr_va; d_asid = lsr_asid
                d_store = lsr_store; d_user = lsr_user
        else:
            d_hit = 0

        if state == I_PTW or state == D_PTW:
            busy = 1
            if mem_v == 1:
                if state == I_PTW:
                    ifu_out_v = 1; ifu_out_pa = (0xBEEF << 12) | (i_va & 0xFFF)
                    ifu_out_pf = 0
                else:
                    lsr_out_v = 1; lsr_out_pa = (0xCAFE << 12) | (d_va & 0xFFF)
                    lsr_out_pf = 0
                next_state = IDLE

        ctx.state['state'] = next_state
        ctx.state['i_hit'] = i_hit; ctx.state['i_vaddr'] = i_va
        ctx.state['d_hit'] = d_hit; ctx.state['d_vaddr'] = d_va
        ctx.state['sv39'] = sv39

        ctx.set_output('ifu_resp_valid', ifu_out_v)
        ctx.set_output('ifu_resp_paddr', ifu_out_pa)
        ctx.set_output('ifu_resp_page_fault', ifu_out_pf)
        ctx.set_output('lsr_resp_valid', lsr_out_v)
        ctx.set_output('lsr_resp_paddr', lsr_out_pa)
        ctx.set_output('lsr_resp_page_fault', lsr_out_pf)
        ctx.set_output('mem_req_valid', mreq_v)
        ctx.set_output('mem_req_addr', mreq_a)
        ctx.set_output('busy', busy)
    return behavior


# =====================================================================
# CSR L2 Cycle-Accurate Model
# =====================================================================


def csr_cycle(**kwargs):
    """L2 cycle-accurate model for CSRFile."""
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            ctx.state['mvendorid'] = 0x9E4
            ctx.state['marchid'] = 0x04
            ctx.state['mimpid'] = 0x01
            ctx.state['mhartid'] = 0x00
            ctx.state['mstatus'] = 0; ctx.state['misa'] = 0
            ctx.state['mie'] = 0; ctx.state['mtvec'] = 0
            ctx.state['mscratch'] = 0; ctx.state['mepc'] = 0
            ctx.state['mcause'] = 0; ctx.state['mtval'] = 0
            ctx.state['mip'] = 0; ctx.state['mcycle'] = 0
            ctx.state['minstret'] = 0
            ctx.state['stvec'] = 0; ctx.state['sscratch'] = 0
            ctx.state['sepc'] = 0; ctx.state['scause'] = 0
            ctx.state['stval'] = 0; ctx.state['satp'] = 0
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('csr_rdata', 0); ctx.set_output('illegal', 0)
            return
        addr = ctx.get_input('csr_addr', 0)
        wdata = ctx.get_input('csr_wdata', 0)
        op = ctx.get_input('csr_op', 0)
        rv = ctx.get_input('retire_valid', 0)
        CSR_MAP = {
            0xF11: 'mvendorid', 0xF12: 'marchid', 0xF13: 'mimpid', 0xF14: 'mhartid',
            0x300: 'mstatus', 0x301: 'misa', 0x304: 'mie', 0x305: 'mtvec',
            0x340: 'mscratch', 0x341: 'mepc', 0x342: 'mcause', 0x343: 'mtval', 0x344: 'mip',
            0xB00: 'mcycle', 0xB02: 'minstret',
            0x100: 'mstatus', 0x104: 'mie', 0x105: 'stvec',
            0x140: 'sscratch', 0x141: 'sepc', 0x142: 'scause', 0x143: 'stval', 0x144: 'mip', 0x180: 'satp',
        }
        RO_ADDRS = {0xF11, 0xF12, 0xF13, 0xF14, 0x344, 0x144}
        S_MASK = {0x100: 0x800000030001E000, 0x104: 0x333, 0x144: 0x333}
        illegal_r = 0 if addr in CSR_MAP else 1
        illegal_w = 1 if (addr not in CSR_MAP) or (addr in RO_ADDRS) else 0
        illegal = 1 if op == 7 else (illegal_r if op == 0 else illegal_w)

        mcycle = ctx.state.get('mcycle', 0)
        minstret = ctx.state.get('minstret', 0)
        mcycle = (mcycle + 1) & 0xFFFFFFFFFFFFFFFF
        if rv == 1:
            minstret = (minstret + 1) & 0xFFFFFFFFFFFFFFFF
        ctx.state['mcycle'] = mcycle
        ctx.state['minstret'] = minstret

        rdata = ctx.state.get(CSR_MAP.get(addr, ''), 0)
        if addr in S_MASK:
            rdata = rdata & S_MASK[addr]

        if (illegal == 0) and (op != 0) and (addr not in RO_ADDRS):
            old = ctx.state.get(CSR_MAP[addr], 0)
            zimm = wdata & 31
            if op == 0: new_val = wdata
            elif op == 1: new_val = wdata
            elif op == 2: new_val = old | wdata
            elif op == 3: new_val = old & ~wdata
            elif op == 4: new_val = zimm
            elif op == 5: new_val = old | zimm
            elif op == 6: new_val = old & ~zimm
            else: new_val = wdata
            if addr == 0x100:
                old_full = ctx.state.get('mstatus', 0)
                ctx.state['mstatus'] = (old_full & ~S_MASK[0x100]) | (new_val & S_MASK[0x100])
            elif addr == 0x104:
                old_full = ctx.state.get('mie', 0)
                ctx.state['mie'] = (old_full & ~0x333) | (new_val & 0x333)
            elif addr == 0xB80:
                old_full = ctx.state.get('mcycle', 0)
                ctx.state['mcycle'] = (new_val << 32) | (old_full & 0xFFFFFFFF)
            elif addr == 0xB82:
                old_full = ctx.state.get('minstret', 0)
                ctx.state['minstret'] = (new_val << 32) | (old_full & 0xFFFFFFFF)
            else:
                ctx.state[CSR_MAP[addr]] = new_val

        ctx.set_output('csr_rdata', rdata)
        ctx.set_output('illegal', illegal)
    return behavior


# =====================================================================
# TAGE L2 Cycle-Accurate Models
# =====================================================================


def tage_table_cycle(**kwargs):
    """L2 cycle-accurate model for TageTable (dual-read single-write)."""
    entries = kwargs.get('entries', 64)
    tag_width = kwargs.get('tag_width', 0)
    ctr_width = kwargs.get('ctr_width', 2)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0
            ctx.state['tag_mem'] = {}; ctx.state['ctr_mem'] = {}
            ctx.state['ubit_mem'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('rd0_tag', 0); ctx.set_output('rd0_ctr', 0)
            ctx.set_output('rd0_ubit', 0); ctx.set_output('rd1_tag', 0)
            ctx.set_output('rd1_ctr', 0); ctx.set_output('rd1_ubit', 0)
            return
        tag_mem = dict(ctx.state.get('tag_mem', {}))
        ctr_mem = dict(ctx.state.get('ctr_mem', {}))
        ubit_mem = dict(ctx.state.get('ubit_mem', {}))
        rd0_i = ctx.get_input('rd0_idx', 0)
        rd1_i = ctx.get_input('rd1_idx', 0)
        wr_i = ctx.get_input('wr_idx', 0)
        wr_tag = ctx.get_input('wr_tag', 0)
        wr_ctr = ctx.get_input('wr_ctr', 0)
        wr_ubit = ctx.get_input('wr_ubit', 0)
        wr_en = ctx.get_input('wr_en', 0)
        if wr_en == 1:
            tag_mem[wr_i] = wr_tag
            ctr_mem[wr_i] = wr_ctr
            ubit_mem[wr_i] = wr_ubit
        ctx.state['tag_mem'] = tag_mem
        ctx.state['ctr_mem'] = ctr_mem
        ctx.state['ubit_mem'] = ubit_mem
        ctx.set_output('rd0_tag', tag_mem.get(rd0_i, 0))
        ctx.set_output('rd0_ctr', ctr_mem.get(rd0_i, 0))
        ctx.set_output('rd0_ubit', ubit_mem.get(rd0_i, 0))
        ctx.set_output('rd1_tag', tag_mem.get(rd1_i, 0))
        ctx.set_output('rd1_ctr', ctr_mem.get(rd1_i, 0))
        ctx.set_output('rd1_ubit', ubit_mem.get(rd1_i, 0))
    return behavior


def stat_corr_cycle(**kwargs):
    """L2 cycle-accurate model for StatisticalCorrector."""
    entries = kwargs.get('entries', 1024)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['mem'] = {}; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('rd0_ctr', 0); ctx.set_output('rd1_ctr', 0); return
        mem = dict(ctx.state.get('mem', {}))
        rd0_i = ctx.get_input('rd0_idx', 0)
        rd1_i = ctx.get_input('rd1_idx', 0)
        wr_i = ctx.get_input('wr_idx', 0)
        wr_ctr = ctx.get_input('wr_ctr', 0)
        wr_en = ctx.get_input('wr_en', 0)
        if wr_en == 1:
            mem[wr_i] = wr_ctr
        ctx.state['mem'] = mem
        ctx.set_output('rd0_ctr', mem.get(rd0_i, 0))
        ctx.set_output('rd1_ctr', mem.get(rd1_i, 0))
    return behavior


def tage_sc_cycle(**kwargs):
    """L2 cycle-accurate model for TageSC (TAGE-SC top)."""
    xlen = kwargs.get('xlen', 40)
    GHR_W = 64
    TABLE_CFG = [
        (64,  0, 2,  0),
        (128, 8, 3,  4),
        (256, 9, 3,  16),
        (512, 10, 3, 48),
    ]
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['ghr'] = 0
            for ti in range(4):
                ctx.state[f'T{ti}_ctr'] = {}
                ctx.state[f'T{ti}_tag'] = {}
                ctx.state[f'T{ti}_ubit'] = {}
            ctx.state['sc_mem'] = {}
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            ctx.set_output('pred_taken', 0); ctx.set_output('pred_alt', 0)
            ctx.set_output('pred_valid', 0); ctx.set_output('global_hist_out', 0)
            return
        ghr = ctx.state.get('ghr', 0)
        req_pc = ctx.get_input('req_pc', 0)
        req_v = ctx.get_input('req_valid', 0)
        upd_pc = ctx.get_input('upd_pc', 0)
        upd_taken = ctx.get_input('upd_taken', 0)
        upd_misp = ctx.get_input('upd_mispredict', 0)
        upd_v = ctx.get_input('upd_valid', 0)
        gh_in = ctx.get_input('global_hist_in', 0)

        # Load table state
        t_ctr = [dict(ctx.state.get(f'T{ti}_ctr', {})) for ti in range(4)]
        t_tag = [dict(ctx.state.get(f'T{ti}_tag', {})) for ti in range(4)]
        t_ubit = [dict(ctx.state.get(f'T{ti}_ubit', {})) for ti in range(4)]
        sc_mem = dict(ctx.state.get('sc_mem', {}))

        def idx_w(entries):
            return max((entries - 1).bit_length(), 1)

        # Prediction: compute hit/pred for each table
        hit = [0] * 4
        pred_s = [0] * 4
        for ti, (entries, tag_w, ctr_w, hist_len) in enumerate(TABLE_CFG):
            iw = idx_w(entries)
            tw = max(tag_w, 1)
            if hist_len > 0:
                xbits = min(hist_len, iw)
                gpart = ghr & ((1 << xbits) - 1)
                gext = gpart if xbits >= iw else gpart
                rd_idx = req_pc & ((1 << iw) - 1) ^ gext
            else:
                rd_idx = req_pc & ((1 << iw) - 1)
            if tag_w > 0:
                ptag = (req_pc >> iw) & ((1 << tag_w) - 1)
                goff = min(hist_len, GHR_W - tag_w)
                gtag = (ghr >> goff) & ((1 << tag_w) - 1)
                computed_tag = ptag ^ gtag
                hit[ti] = 1 if t_tag[ti].get(rd_idx, 0) == computed_tag else 0
                pred_s[ti] = 1 if t_ctr[ti].get(rd_idx, 0) >= 4 else 0
            else:
                hit[ti] = 1
                pred_s[ti] = 1 if t_ctr[ti].get(rd_idx, 0) >= 2 else 0

        # Provider selection
        if hit[3]: p_pred = pred_s[3]
        elif hit[2]: p_pred = pred_s[2]
        elif hit[1]: p_pred = pred_s[1]
        else: p_pred = pred_s[0]

        # Altpred
        if hit[3] and hit[2]: a_pred = pred_s[2]
        elif hit[3] and hit[1]: a_pred = pred_s[1]
        elif hit[3] and hit[0]: a_pred = pred_s[0]
        elif hit[2] and hit[1]: a_pred = pred_s[1]
        elif hit[2] and hit[0]: a_pred = pred_s[0]
        elif hit[1]: a_pred = pred_s[0]
        else: a_pred = pred_s[0]

        # SC
        sc_idx = (req_pc & 0x3FF) ^ (ghr & 0x3FF)
        sc0 = sc_mem.get(sc_idx, 0)
        if sc0 == 0: pred_taken = 0
        elif sc0 == 3: pred_taken = 1
        else: pred_taken = p_pred

        # Update
        if upd_v == 1:
            ghr = ((ghr << 1) | upd_taken) & ((1 << GHR_W) - 1)

            # Update index computation for each table
            upd_idx = []
            for ti, (entries, tag_w, ctr_w, hist_len) in enumerate(TABLE_CFG):
                iw = idx_w(entries)
                if hist_len > 0:
                    xbits = min(hist_len, iw)
                    gpart = ghr & ((1 << xbits) - 1)
                    gext = gpart if xbits >= iw else gpart
                    ui = upd_pc & ((1 << iw) - 1) ^ gext
                else:
                    ui = upd_pc & ((1 << iw) - 1)
                upd_idx.append(ui)

            # Update hit at update time
            upd_hit = [0] * 4
            upd_tpred = [0] * 4
            for ti, (entries, tag_w, ctr_w, hist_len) in enumerate(TABLE_CFG):
                iw = idx_w(entries)
                tw = max(tag_w, 1)
                if tag_w > 0:
                    ptag = (upd_pc >> iw) & ((1 << tag_w) - 1)
                    goff = min(hist_len, GHR_W - tag_w)
                    gtag = (ghr >> goff) & ((1 << tag_w) - 1)
                    utag = ptag ^ gtag
                    upd_hit[ti] = 1 if t_tag[ti].get(upd_idx[ti], 0) == utag else 0
                    upd_tpred[ti] = 1 if t_ctr[ti].get(upd_idx[ti], 0) >= 4 else 0
                else:
                    upd_hit[ti] = 1
                    upd_tpred[ti] = 1 if t_ctr[ti].get(upd_idx[ti], 0) >= 2 else 0

            # Update T0 base counter
            c0 = t_ctr[0].get(upd_idx[0], 0)
            if upd_taken:
                nc0 = c0 + 1 if c0 < 3 else c0
            else:
                nc0 = c0 - 1 if c0 > 0 else c0
            t_ctr[0][upd_idx[0]] = nc0

            # Update T1/T2/T3 provider (correct only)
            if upd_misp == 0:
                for ti in range(3, 0, -1):
                    if upd_hit[ti]:
                        ci = t_ctr[ti].get(upd_idx[ti], 0)
                        if upd_taken:
                            nci = ci + 1 if ci < 7 else ci
                        else:
                            nci = ci - 1 if ci > 0 else ci
                        t_ctr[ti][upd_idx[ti]] = nci
                        # u-bit
                        if ti == 3:
                            ap = upd_tpred[2] if upd_hit[2] else (upd_tpred[1] if upd_hit[1] else upd_tpred[0])
                        elif ti == 2:
                            ap = upd_tpred[1] if upd_hit[1] else upd_tpred[0]
                        else:
                            ap = upd_tpred[0]
                        ui_val = t_ubit[ti].get(upd_idx[ti], 0)
                        if upd_tpred[ti] != ap:
                            t_ubit[ti][upd_idx[ti]] = 1
                        else:
                            t_ubit[ti][upd_idx[ti]] = 0 if ui_val > 0 else 0
                        break

            # Allocate on mispredict
            if upd_misp == 1:
                ti = 3
                entries3, tag_w3, ctr_w3, _ = TABLE_CFG[3]
                iw3 = idx_w(entries3)
                tw3 = max(tag_w3, 1)
                ptag3 = (upd_pc >> iw3) & ((1 << tag_w3) - 1)
                goff3 = min(TABLE_CFG[3][3], GHR_W - tag_w3)
                gtag3 = (ghr >> goff3) & ((1 << tag_w3) - 1)
                t_tag[3][upd_idx[3]] = ptag3 ^ gtag3
                t_ctr[3][upd_idx[3]] = 4 if upd_taken else 3
                t_ubit[3][upd_idx[3]] = 0

            # SC update
            sc_upd_idx = (upd_pc & 0x3FF) ^ (ghr & 0x3FF)
            sci = sc_mem.get(sc_upd_idx, 0)
            if upd_taken:
                nsci = sci + 1 if sci < 3 else sci
            else:
                nsci = sci - 1 if sci > 0 else sci
            sc_mem[sc_upd_idx] = nsci

        # Save state
        ctx.state['ghr'] = ghr
        for ti in range(4):
            ctx.state[f'T{ti}_ctr'] = t_ctr[ti]
            ctx.state[f'T{ti}_tag'] = t_tag[ti]
            ctx.state[f'T{ti}_ubit'] = t_ubit[ti]
        ctx.state['sc_mem'] = sc_mem

        ctx.set_output('pred_taken', pred_taken)
        ctx.set_output('pred_alt', a_pred)
        ctx.set_output('pred_valid', req_v)
        ctx.set_output('global_hist_out', ghr)
    return behavior


# =====================================================================
# OoO Sub-Module L2 Cycle-Accurate Models
# =====================================================================


def reservation_station_cycle(**kwargs):
    """L2 cycle-accurate model for ReservationStation."""
    entries = kwargs.get('entries', 8)
    pr_num = kwargs.get('pr_num', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['head'] = 0
            ctx.state['tail'] = 0; ctx.state['cnt'] = 0
            ctx.state['op_t'] = {}; ctx.state['prd_t'] = {}
            ctx.state['prs1_t'] = {}; ctx.state['prs2_t'] = {}
            ctx.state['rdy1_t'] = {}; ctx.state['rdy2_t'] = {}
            ctx.state['vld_t'] = {}
            return
        init = ctx.state.get('init', 0)
        head = ctx.state.get('head', 0); tail = ctx.state.get('tail', 0)
        cnt = ctx.state.get('cnt', 0)
        op_t = dict(ctx.state.get('op_t', {})); prd_t = dict(ctx.state.get('prd_t', {}))
        prs1_t = dict(ctx.state.get('prs1_t', {})); prs2_t = dict(ctx.state.get('prs2_t', {}))
        rdy1_t = dict(ctx.state.get('rdy1_t', {})); rdy2_t = dict(ctx.state.get('rdy2_t', {}))
        vld_t = dict(ctx.state.get('vld_t', {}))
        dispatch = ctx.get_input('dispatch', 0)
        op = ctx.get_input('op', 0); prs1 = ctx.get_input('prs1', 0)
        prs2 = ctx.get_input('prs2', 0); prd = ctx.get_input('prd', 0)
        wakeup_pr = ctx.get_input('wakeup_pr', 0)
        wakeup_en = ctx.get_input('wakeup_en', 0)
        issue_ready = ctx.get_input('issue_ready', 0)

        if init == 0:
            ctx.state['init'] = 1
            ctx.set_output('issue_op', 0); ctx.set_output('issue_prd', 0)
            ctx.set_output('issue_valid', 0); ctx.set_output('full', 0)
            return

        # Oldest-ready select (combinational)
        issue_hit = 0; issue_idx = head
        for i in range(entries):
            idx = (head + i) % entries
            r1e = (rdy1_t.get(idx, 0) == 1) or (prs1_t.get(idx, 0) == 0)
            r2e = (rdy2_t.get(idx, 0) == 1) or (prs2_t.get(idx, 0) == 0)
            if (vld_t.get(idx, 0) == 1) and r1e and r2e and (issue_hit == 0):
                issue_hit = 1; issue_idx = idx

        do_dispatch = (dispatch == 1) and (cnt < entries)
        do_issue = (issue_hit == 1) and (issue_ready == 1)

        if do_dispatch == 1:
            op_t[tail] = op; prd_t[tail] = prd
            prs1_t[tail] = prs1; prs2_t[tail] = prs2
            rdy1_t[tail] = 0; rdy2_t[tail] = 0; vld_t[tail] = 1
            tail = (tail + 1) % entries
            cnt += 1

        if wakeup_en == 1:
            for i in range(entries):
                if vld_t.get(i, 0) == 1 and prs1_t.get(i, 0) == wakeup_pr:
                    rdy1_t[i] = 1
                if vld_t.get(i, 0) == 1 and prs2_t.get(i, 0) == wakeup_pr:
                    rdy2_t[i] = 1

        if do_issue == 1:
            vld_t[issue_idx] = 0
            if issue_idx == head:
                head = (head + 1) % entries
            cnt -= 1

        ctx.state['head'] = head; ctx.state['tail'] = tail; ctx.state['cnt'] = cnt
        ctx.state['op_t'] = op_t; ctx.state['prd_t'] = prd_t
        ctx.state['prs1_t'] = prs1_t; ctx.state['prs2_t'] = prs2_t
        ctx.state['rdy1_t'] = rdy1_t; ctx.state['rdy2_t'] = rdy2_t; ctx.state['vld_t'] = vld_t

        ctx.set_output('issue_op', op_t.get(issue_idx, 0))
        ctx.set_output('issue_prd', prd_t.get(issue_idx, 0))
        ctx.set_output('issue_valid', issue_hit)
        ctx.set_output('full', 1 if cnt >= entries else 0)
    return behavior


def dispatch_unit_cycle(**kwargs):
    """L2 cycle-accurate model for DispatchUnit (6-wide)."""
    pr_num = kwargs.get('pr_num', 64)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            for i in range(6):
                ctx.set_output(f'dispatch_{i}', 0)
                ctx.set_output(f'dispatch_op_{i}', 0)
                ctx.set_output(f'dispatch_prs1_{i}', 0)
                ctx.set_output(f'dispatch_prs2_{i}', 0)
                ctx.set_output(f'dispatch_prd_{i}', 0)
            return
        for i in range(6):
            sv = ctx.get_input(f'slot_valid_{i}', 0)
            rf = ctx.get_input(f'rs_full_{i}', 0)
            ctx.set_output(f'dispatch_{i}', 1 if (sv == 1) and (rf == 0) else 0)
            ctx.set_output(f'dispatch_op_{i}', ctx.get_input(f'slot_op_{i}', 0))
            ctx.set_output(f'dispatch_prs1_{i}', ctx.get_input(f'slot_prs1_{i}', 0))
            ctx.set_output(f'dispatch_prs2_{i}', ctx.get_input(f'slot_prs2_{i}', 0))
            ctx.set_output(f'dispatch_prd_{i}', ctx.get_input(f'slot_prd_{i}', 0))
    return behavior


def ooo_core_cycle(**kwargs):
    """L2 cycle-accurate model for OoOCore (simplified pipeline)."""
    rs_entries = kwargs.get('rs_entries', 8)
    pr_num = kwargs.get('pr_num', 64)
    log_pr = max((pr_num - 1).bit_length(), 1)
    def behavior(ctx):
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['init'] = 0; ctx.state['rs_vld'] = [0]*6
            ctx.state['rs_op'] = [0]*6; ctx.state['rs_prd'] = [0]*6
            ctx.state['rs_prs1'] = [0]*6; ctx.state['rs_prs2'] = [0]*6
            ctx.state['rs_rdy1'] = [0]*6; ctx.state['rs_rdy2'] = [0]*6
            ctx.state['ex_v'] = [0]*6; ctx.state['ex_d'] = [0]*6
            ctx.state['ex_p'] = [0]*6
            return
        if ctx.state.get('init', 0) == 0:
            ctx.state['init'] = 1
            for i in range(6):
                ctx.set_output(f'commit_valid_{i}', 0)
                ctx.set_output(f'commit_prd_{i}', 0)
                ctx.set_output(f'commit_data_{i}', 0)
            return
        rs_vld = list(ctx.state.get('rs_vld', [0]*6))
        rs_op = list(ctx.state.get('rs_op', [0]*6))
        rs_prd = list(ctx.state.get('rs_prd', [0]*6))
        rs_prs1 = list(ctx.state.get('rs_prs1', [0]*6))
        rs_prs2 = list(ctx.state.get('rs_prs2', [0]*6))
        rs_rdy1 = list(ctx.state.get('rs_rdy1', [0]*6))
        rs_rdy2 = list(ctx.state.get('rs_rdy2', [0]*6))
        ex_v = list(ctx.state.get('ex_v', [0]*6))
        ex_d = list(ctx.state.get('ex_d', [0]*6))
        ex_p = list(ctx.state.get('ex_p', [0]*6))

        # Dispatch
        for i in range(6):
            sv = ctx.get_input(f'slot_valid_{i}', 0)
            if sv == 1 and not rs_vld[i]:
                rs_vld[i] = 1
                rs_op[i] = ctx.get_input(f'slot_op_{i}', 0)
                rs_prs1[i] = ctx.get_input(f'slot_prs1_{i}', 0)
                rs_prs2[i] = ctx.get_input(f'slot_prs2_{i}', 0)
                rs_prd[i] = ctx.get_input(f'slot_prd_{i}', 0)
                rs_rdy1[i] = 1 if rs_prs1[i] == 0 else 0
                rs_rdy2[i] = 1 if rs_prs2[i] == 0 else 0

        # Wakeup: broadcast all commit results
        for i in range(6):
            if ex_v[i]:
                for j in range(6):
                    if rs_vld[j] and rs_prs1[j] == ex_p[i]:
                        rs_rdy1[j] = 1
                    if rs_vld[j] and rs_prs2[j] == ex_p[i]:
                        rs_rdy2[j] = 1

        # Issue: oldest-ready selected
        for i in range(6):
            if rs_vld[i] and rs_rdy1[i] and rs_rdy2[i] and not ex_v[i]:
                ex_v[i] = 1
                ex_d[i] = rs_op[i]
                ex_p[i] = rs_prd[i]
                rs_vld[i] = 0
                break

        ctx.state['rs_vld'] = rs_vld; ctx.state['rs_op'] = rs_op
        ctx.state['rs_prd'] = rs_prd; ctx.state['rs_prs1'] = rs_prs1
        ctx.state['rs_prs2'] = rs_prs2
        ctx.state['rs_rdy1'] = rs_rdy1; ctx.state['rs_rdy2'] = rs_rdy2
        ctx.state['ex_v'] = ex_v; ctx.state['ex_d'] = ex_d; ctx.state['ex_p'] = ex_p

        for i in range(6):
            ctx.set_output(f'commit_valid_{i}', ex_v[i])
            ctx.set_output(f'commit_prd_{i}', ex_p[i])
            ctx.set_output(f'commit_data_{i}', ex_d[i])
    return behavior


# =====================================================================
# RTU Sub-Module Registry
# =====================================================================

TemplateRegistry.register('rob', rob_cycle)
TemplateRegistry.register('commit_unit', commit_unit_cycle)
TemplateRegistry.register('pst', pst_cycle)
TemplateRegistry.register('pst_extra', pst_extra_cycle)
TemplateRegistry.register('retire_unit', retire_unit_cycle)

# =====================================================================
# MMU Sub-Module Registry
# =====================================================================

TemplateRegistry.register('itlb', itlb_cycle)
TemplateRegistry.register('dtlb', dtlb_cycle)
TemplateRegistry.register('l2tlb', l2tlb_cycle)
TemplateRegistry.register('ptw', ptw_cycle)
TemplateRegistry.register('mmu', mmu_cycle)

# =====================================================================
# CSR Sub-Module Registry
# =====================================================================

TemplateRegistry.register('csr', csr_cycle)

# =====================================================================
# TAGE Sub-Module Registry
# =====================================================================

TemplateRegistry.register('tage_table', tage_table_cycle)
TemplateRegistry.register('stat_corr', stat_corr_cycle)
TemplateRegistry.register('tage_sc', tage_sc_cycle)

# =====================================================================
# OoO Sub-Module Registry
# =====================================================================

TemplateRegistry.register('reservation_station', reservation_station_cycle)
TemplateRegistry.register('dispatch_unit', dispatch_unit_cycle)
TemplateRegistry.register('ooo_core', ooo_core_cycle)

# =====================================================================
# LSU Sub-Module Registry (existing)
# =====================================================================

TemplateRegistry.register('lsu', lsu_cycle)
TemplateRegistry.register('ls_addrgen', ls_addrgen_cycle)
TemplateRegistry.register('atomic_op', atomic_op_cycle)
TemplateRegistry.register('bus_arb', bus_arb_cycle)
TemplateRegistry.register('cache_buffer', cache_buffer_cycle)
TemplateRegistry.register('lsu_ctrl', lsu_ctrl_cycle)
TemplateRegistry.register('dcache_if', dcache_if_cycle)
TemplateRegistry.register('dcache_top', dcache_top_cycle)
TemplateRegistry.register('icc', icc_cycle)
TemplateRegistry.register('load_addr_gen', load_addr_gen_cycle)
TemplateRegistry.register('load_data_array', load_data_array_cycle)
TemplateRegistry.register('ls_data_check', ls_data_check_cycle)
TemplateRegistry.register('lfb', lfb_cycle)
TemplateRegistry.register('load_miss', load_miss_cycle)
TemplateRegistry.register('mcic', mcic_cycle)
TemplateRegistry.register('prefetch_unit', prefetch_unit_cycle)
TemplateRegistry.register('load_queue', load_queue_cycle)
TemplateRegistry.register('store_queue', store_queue_cycle)
TemplateRegistry.register('ls_reorder_buf', ls_reorder_buf_cycle)
TemplateRegistry.register('store_data_ext', store_data_ext_cycle)
TemplateRegistry.register('snoop_ctrl', snoop_ctrl_cycle)
TemplateRegistry.register('snoop_ctrl_tq', snoop_ctrl_tq_cycle)
TemplateRegistry.register('snoop_req_arb', snoop_req_arb_cycle)
TemplateRegistry.register('snoop_resp', snoop_resp_cycle)
TemplateRegistry.register('snoop_snq', snoop_snq_cycle)
TemplateRegistry.register('spec_fail_predict', spec_fail_predict_cycle)
TemplateRegistry.register('store_addr_gen', store_addr_gen_cycle)
TemplateRegistry.register('store_data_array', store_data_array_cycle)
TemplateRegistry.register('victim_buffer', victim_buffer_cycle)
TemplateRegistry.register('vb_store_data', vb_store_data_cycle)
TemplateRegistry.register('load_writeback', load_writeback_cycle)
TemplateRegistry.register('store_writeback', store_writeback_cycle)
TemplateRegistry.register('wmb', wmb_cycle)
