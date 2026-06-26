"""
skills.cpu.test_l2_batch — L2 cycle-level model cross-layer verification.

For each IFU sub-module:
  - Import L2 model from cycle_level.py
  - Import L3 DSL class
  - Create 2-3 test cases
  - Verify via LayerVerifier

Usage:  python -m skills.cpu.test_l2_batch
"""
import sys; sys.path.insert(0, '.')
import importlib.util
from typing import Any, Callable, Dict, List

from rtlgen.forward import LayerVerifier
from skills.cpu.cycle_level import (
    pcgen_cycle, bpred_cycle, addrgen_cycle, icache_if_cycle,
    ifctrl_cycle, lbuf_cycle, ind_btb_cycle, predecode_cycle,
    pcfifo_cycle, vec_fetch_cycle, l1_refill_cycle, sfp_cycle, ifu_debug_cycle,
)


def _l3_class(mod_name: str, cls_name: str):
    """Load an L3 DSL class dynamically."""
    spec = importlib.util.spec_from_file_location(
        mod_name, f'skills/cpu/layer3_dsl/{mod_name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return getattr(m, cls_name)


def run_verification(
    module_name: str,
    l2_func: Callable,
    l3_class: type,
    l1_func: Any = None,
    test_cases: List[Dict] = None,
    sim_cycles: int = 10,
) -> bool:
    """Run LayerVerifier and print result."""
    if l1_func is not None:
        l1_tag = 'with L1'
    else:
        l1_tag = 'no L1'
    print(f'  Verifying {module_name} ({l1_tag})...', end=' ')
    try:
        ok = LayerVerifier.verify(
            module_name, l1_func, l3_class,
            test_cases=test_cases or [],
            l2_func=l2_func,
            sim_cycles=sim_cycles,
        )
        status = 'PASS' if ok else 'FAIL'
        print(status)
        return ok
    except Exception as e:
        print(f'ERROR: {e}')
        return False


# =====================================================================
# Test suites for each module
# =====================================================================

def test_pcgen():
    cls = _l3_class('pcgen', 'PCGen')
    from skills.cpu.functional import ifu_pcgen_functional
    cases = [
        {
            'tag': 'pcgen_seq',
            'l3_inputs': {'rv': 0, 'rpc': 0, 'stall': 0},
            'l2_inputs': {'rv': 0, 'rpc': 0, 'stall': 0},
            'expect': {'pc': 40, 'pc_chg': 0},
        },
        {
            'tag': 'pcgen_redirect',
            'l3_inputs': {'rv': 1, 'rpc': 0x2000, 'stall': 0},
            'l2_inputs': {'rv': 1, 'rpc': 0x2000, 'stall': 0},
            'expect': {'pc': 0x2000, 'pc_chg': 1},
        },
        {
            'tag': 'pcgen_stall',
            'l3_inputs': {'rv': 0, 'rpc': 0, 'stall': 1},
            'l2_inputs': {'rv': 0, 'rpc': 0, 'stall': 1},
            'expect': {'pc': 0, 'pc_chg': 0},
        },
    ]
    return run_verification('PCGen', pcgen_cycle, cls, l1_func=None, test_cases=cases)


def test_bpred():
    cls = _l3_class('bpred', 'BPred')
    cases = [
        {
            'tag': 'bpred_idle',
            'l3_inputs': {'req_pc': 0, 'req_valid': 0, 'upd_pc': 0, 'upd_taken': 0,
                          'upd_target': 0, 'upd_valid': 0, 'upd_is_call': 0, 'upd_is_return': 0},
            'l2_inputs': {'req_pc': 0, 'req_valid': 0, 'upd_pc': 0, 'upd_taken': 0,
                          'upd_target': 0, 'upd_valid': 0, 'upd_is_call': 0, 'upd_is_return': 0},
            'expect': {'pred_taken': 0, 'pred_target': 0, 'pred_valid': 0},
        },
        {
            'tag': 'bpred_req_no_btb',
            'l3_inputs': {'req_pc': 0x1000, 'req_valid': 1, 'upd_pc': 0, 'upd_taken': 0,
                          'upd_target': 0, 'upd_valid': 0, 'upd_is_call': 0, 'upd_is_return': 0},
            'l2_inputs': {'req_pc': 0x1000, 'req_valid': 1, 'upd_pc': 0, 'upd_taken': 0,
                          'upd_target': 0, 'upd_valid': 0, 'upd_is_call': 0, 'upd_is_return': 0},
            'expect': {'pred_taken': 0, 'pred_target': 0, 'pred_valid': 0},
        },
        {
            'tag': 'bpred_ras_call',
            'l3_inputs': {'req_pc': 0, 'req_valid': 0, 'upd_pc': 0x2000, 'upd_taken': 0,
                          'upd_target': 0, 'upd_valid': 0, 'upd_is_call': 1, 'upd_is_return': 0},
            'l2_inputs': {'req_pc': 0, 'req_valid': 0, 'upd_pc': 0x2000, 'upd_taken': 0,
                          'upd_target': 0, 'upd_valid': 0, 'upd_is_call': 1, 'upd_is_return': 0},
            'expect': {'pred_taken': 0, 'pred_target': 0, 'pred_valid': 0},
        },
    ]
    return run_verification('BPred', bpred_cycle, cls, l1_func=None, test_cases=cases)


def test_addrgen():
    cls = _l3_class('ifu_common', 'AddrGen')
    cases = [
        {
            'tag': 'addrgen_normal',
            'l3_inputs': {'pc': 0x1000, 'redirect': 0, 'redirect_pc': 0, 'stall': 0},
            'l2_inputs': {'pc': 0x1000, 'redirect': 0, 'redirect_pc': 0, 'stall': 0},
            'expect': {'fetch_addr': 0x1000, 'fetch_valid': 1},
        },
        {
            'tag': 'addrgen_redirect',
            'l3_inputs': {'pc': 0x1000, 'redirect': 1, 'redirect_pc': 0x2000, 'stall': 0},
            'l2_inputs': {'pc': 0x1000, 'redirect': 1, 'redirect_pc': 0x2000, 'stall': 0},
            'expect': {'fetch_addr': 0x2000, 'fetch_valid': 1},
        },
        {
            'tag': 'addrgen_stall',
            'l3_inputs': {'pc': 0x1000, 'redirect': 0, 'redirect_pc': 0, 'stall': 1},
            'l2_inputs': {'pc': 0x1000, 'redirect': 0, 'redirect_pc': 0, 'stall': 1},
            'expect': {'fetch_addr': 0x1000, 'fetch_valid': 0},
        },
    ]
    return run_verification('AddrGen', addrgen_cycle, cls, l1_func=None, test_cases=cases)


def test_icache_if():
    cls = _l3_class('ifu_common', 'ICacheIF')
    cases = [
        {
            'tag': 'icache_idle',
            'l3_inputs': {'req_addr': 0, 'req_valid': 0, 'cache_rdata': 0,
                          'cache_ready': 0, 'flush': 0},
            'l2_inputs': {'req_addr': 0, 'req_valid': 0, 'cache_rdata': 0,
                          'cache_ready': 0, 'flush': 0},
            'expect': {'req_ready': 1, 'rdata': 0, 'rvalid': 0, 'miss': 0},
        },
        {
            'tag': 'icache_req_with_ready',
            'l3_inputs': {'req_addr': 0x1000, 'req_valid': 1, 'cache_rdata': 0xDEAD,
                          'cache_ready': 1, 'flush': 0},
            'l2_inputs': {'req_addr': 0x1000, 'req_valid': 1, 'cache_rdata': 0xDEAD,
                          'cache_ready': 1, 'flush': 0},
            'expect': {'req_ready': 1, 'rdata': 0xDEAD, 'rvalid': 0, 'miss': 0},
        },
        {
            'tag': 'icache_pending_no_ready',
            'l3_inputs': {'req_addr': 0x1000, 'req_valid': 1, 'cache_rdata': 0,
                          'cache_ready': 0, 'flush': 0},
            'l2_inputs': {'req_addr': 0x1000, 'req_valid': 1, 'cache_rdata': 0,
                          'cache_ready': 0, 'flush': 0},
            'expect': {'req_ready': 0, 'rdata': 0, 'rvalid': 0, 'miss': 0},
        },
    ]
    return run_verification('ICacheIF', icache_if_cycle, cls, l1_func=None, test_cases=cases)


def test_ifctrl():
    cls = _l3_class('ifu_common', 'IFCtrl')
    cases = [
        {
            'tag': 'ifctrl_normal',
            'l3_inputs': {'branch_taken': 0, 'branch_target': 0,
                          'icache_miss': 0, 'ibuf_full': 0, 'flush': 0},
            'l2_inputs': {'branch_taken': 0, 'branch_target': 0,
                          'icache_miss': 0, 'ibuf_full': 0, 'flush': 0},
            'expect': {'redirect': 0, 'redirect_pc': 0, 'stall_fetch': 0},
        },
        {
            'tag': 'ifctrl_branch',
            'l3_inputs': {'branch_taken': 1, 'branch_target': 0x3000,
                          'icache_miss': 0, 'ibuf_full': 0, 'flush': 0},
            'l2_inputs': {'branch_taken': 1, 'branch_target': 0x3000,
                          'icache_miss': 0, 'ibuf_full': 0, 'flush': 0},
            'expect': {'redirect': 1, 'redirect_pc': 0x3000, 'stall_fetch': 0},
        },
        {
            'tag': 'ifctrl_stall',
            'l3_inputs': {'branch_taken': 0, 'branch_target': 0,
                          'icache_miss': 1, 'ibuf_full': 1, 'flush': 0},
            'l2_inputs': {'branch_taken': 0, 'branch_target': 0,
                          'icache_miss': 1, 'ibuf_full': 1, 'flush': 0},
            'expect': {'redirect': 0, 'redirect_pc': 0, 'stall_fetch': 1},
        },
    ]
    return run_verification('IFCtrl', ifctrl_cycle, cls, l1_func=None, test_cases=cases)


def test_lbuf():
    cls = _l3_class('ifu_common', 'LBuf')
    cases = [
        {
            'tag': 'lbuf_fill_read',
            'l3_inputs': {'fill': 1, 'fill_data': 0xABCD, 'fill_idx': 5,
                          'loop_active': 0, 'loop_start': 0, 'loop_end': 0, 'rd_idx': 5},
            'l2_inputs': {'fill': 1, 'fill_data': 0xABCD, 'fill_idx': 5,
                          'loop_active': 0, 'loop_start': 0, 'loop_end': 0, 'rd_idx': 5},
            'expect': {'rdata': 0xABCD, 'rhit': 0},
        },
        {
            'tag': 'lbuf_loop_hit',
            'l3_inputs': {'fill': 1, 'fill_data': 0x1234, 'fill_idx': 3,
                          'loop_active': 1, 'loop_start': 0, 'loop_end': 7, 'rd_idx': 3},
            'l2_inputs': {'fill': 1, 'fill_data': 0x1234, 'fill_idx': 3,
                          'loop_active': 1, 'loop_start': 0, 'loop_end': 7, 'rd_idx': 3},
            'expect': {'rdata': 0x1234, 'rhit': 1},
        },
        {
            'tag': 'lbuf_loop_miss',
            'l3_inputs': {'fill': 0, 'fill_data': 0, 'fill_idx': 0,
                          'loop_active': 1, 'loop_start': 0, 'loop_end': 3, 'rd_idx': 7},
            'l2_inputs': {'fill': 0, 'fill_data': 0, 'fill_idx': 0,
                          'loop_active': 1, 'loop_start': 0, 'loop_end': 3, 'rd_idx': 7},
            'expect': {'rdata': 0, 'rhit': 0},
        },
    ]
    return run_verification('LBuf', lbuf_cycle, cls, l1_func=None, test_cases=cases)


def test_ind_btb():
    cls = _l3_class('ifu_ind_btb', 'IndirectBranchBTB')
    cases = [
        {
            'tag': 'indbtb_idle',
            'l3_inputs': {'req_pc': 0, 'req_valid': 0, 'upd_pc': 0,
                          'upd_target': 0, 'upd_valid': 0},
            'l2_inputs': {'req_pc': 0, 'req_valid': 0, 'upd_pc': 0,
                          'upd_target': 0, 'upd_valid': 0},
            'expect': {'pred_target': 0, 'pred_valid': 0},
        },
        {
            'tag': 'indbtb_update_hit',
            'l3_inputs': {'req_pc': 0x1000, 'req_valid': 1, 'upd_pc': 0x1000,
                          'upd_target': 0x2000, 'upd_valid': 1},
            'l2_inputs': {'req_pc': 0x1000, 'req_valid': 1, 'upd_pc': 0x1000,
                          'upd_target': 0x2000, 'upd_valid': 1},
            'expect': {'pred_target': 0x2000, 'pred_valid': 1},
        },
        {
            'tag': 'indbtb_miss',
            'l3_inputs': {'req_pc': 0x3000, 'req_valid': 1, 'upd_pc': 0x1000,
                          'upd_target': 0x2000, 'upd_valid': 1},
            'l2_inputs': {'req_pc': 0x3000, 'req_valid': 1, 'upd_pc': 0x1000,
                          'upd_target': 0x2000, 'upd_valid': 1},
            'expect': {'pred_target': 0x2000, 'pred_valid': 0},
        },
    ]
    return run_verification('IndirectBranchBTB', ind_btb_cycle, cls, l1_func=None, test_cases=cases)


def test_predecode():
    cls = _l3_class('ifu_predecode', 'PreDecodeBuffer')
    cases = [
        {
            'tag': 'predecode_flush',
            'l3_inputs': {'push_valid': 0, 'push_instr': 0, 'push_tag': 0,
                          'pop_ready': 0, 'flush': 1},
            'l2_inputs': {'push_valid': 0, 'push_instr': 0, 'push_tag': 0,
                          'pop_ready': 0, 'flush': 1},
            'expect': {'instr': 0, 'tag': 0, 'valid': 0, 'stall': 0, 'free_slots': 4},
        },
        {
            'tag': 'predecode_push_only',
            'l3_inputs': {'push_valid': 1, 'push_instr': 0xBEEF, 'push_tag': 0xBB,
                          'pop_ready': 0, 'flush': 0},
            'l2_inputs': {'push_valid': 1, 'push_instr': 0xBEEF, 'push_tag': 0xBB,
                          'pop_ready': 0, 'flush': 0},
            'expect': {'instr': 0xBEEF, 'tag': 0xBB, 'valid': 1, 'stall': 0, 'free_slots': 3},
        },
        {
            'tag': 'predecode_push_pop',
            'l3_inputs': {'push_valid': 1, 'push_instr': 0xCAFE, 'push_tag': 0xCC,
                          'pop_ready': 1, 'flush': 0},
            'l2_inputs': {'push_valid': 1, 'push_instr': 0xCAFE, 'push_tag': 0xCC,
                          'pop_ready': 1, 'flush': 0},
            'expect': {'instr': 0xCAFE, 'tag': 0xCC, 'valid': 1, 'stall': 0, 'free_slots': 3},
        },
    ]
    return run_verification('PreDecodeBuffer', predecode_cycle, cls, l1_func=None, test_cases=cases, sim_cycles=1)


def test_pcfifo():
    cls = _l3_class('ifu_pcfifo', 'PCFifo')
    cases = [
        {
            'tag': 'pcfifo_idle',
            'l3_inputs': {'push_pc': 0, 'push_valid': 0, 'pop': 0, 'flush': 0},
            'l2_inputs': {'push_pc': 0, 'push_valid': 0, 'pop': 0, 'flush': 0},
            'expect': {'top_pc': 0, 'top_valid': 0, 'free': 8},
        },
        {
            'tag': 'pcfifo_push_only',
            'l3_inputs': {'push_pc': 0x1000, 'push_valid': 1, 'pop': 0, 'flush': 0},
            'l2_inputs': {'push_pc': 0x1000, 'push_valid': 1, 'pop': 0, 'flush': 0},
            'expect': {'top_pc': 0x1000, 'top_valid': 1, 'free': 7},
        },
        {
            'tag': 'pcfifo_flush',
            'l3_inputs': {'push_pc': 0x2000, 'push_valid': 1, 'pop': 0, 'flush': 1},
            'l2_inputs': {'push_pc': 0x2000, 'push_valid': 1, 'pop': 0, 'flush': 1},
            'expect': {'top_pc': 0, 'top_valid': 0, 'free': 8},
        },
    ]
    return run_verification('PCFifo', pcfifo_cycle, cls, l1_func=None, test_cases=cases, sim_cycles=1)


def test_vec_fetch():
    cls = _l3_class('ifu_vector', 'VectorFetch')
    cases = [
        {
            'tag': 'vec_idle',
            'l3_inputs': {'start': 0, 'start_pc': 0, 'vlen': 0, 'fetch_ready': 0},
            'l2_inputs': {'start': 0, 'start_pc': 0, 'vlen': 0, 'fetch_ready': 0},
            'expect': {'fetch_addr': 0, 'fetch_valid': 0, 'busy': 0, 'done': 0},
        },
        {
            'tag': 'vec_start_one',
            'l3_inputs': {'start': 1, 'start_pc': 0x1000, 'vlen': 1, 'fetch_ready': 1},
            'l2_inputs': {'start': 1, 'start_pc': 0x1000, 'vlen': 1, 'fetch_ready': 1},
            'expect': {'fetch_addr': 0x1000, 'fetch_valid': 1, 'busy': 1, 'done': 1},
        },
        {
            'tag': 'vec_start_multi',
            'l3_inputs': {'start': 1, 'start_pc': 0x2000, 'vlen': 4, 'fetch_ready': 1},
            'l2_inputs': {'start': 1, 'start_pc': 0x2000, 'vlen': 4, 'fetch_ready': 1},
            'expect': {'fetch_addr': 0x2000, 'fetch_valid': 1, 'busy': 1, 'done': 0},
        },
    ]
    return run_verification('VectorFetch', vec_fetch_cycle, cls, l1_func=None, test_cases=cases, sim_cycles=1)


def test_l1_refill():
    cls = _l3_class('ifu_l1_refill', 'L1Refill')
    cases = [
        {
            'tag': 'refill_idle',
            'l3_inputs': {'miss_addr': 0, 'miss_valid': 0, 'l2_rdata': 0, 'l2_ready': 0},
            'l2_inputs': {'miss_addr': 0, 'miss_valid': 0, 'l2_rdata': 0, 'l2_ready': 0},
            'expect': {'refill_addr': 0, 'refill_req': 0, 'refill_data': 0, 'refill_done': 0, 'busy': 0},
        },
        {
            'tag': 'refill_full_seq',
            'l3_inputs': {'miss_addr': 0x1000, 'miss_valid': 1, 'l2_rdata': 0xCAFE, 'l2_ready': 1},
            'l2_inputs': {'miss_addr': 0x1000, 'miss_valid': 1, 'l2_rdata': 0xCAFE, 'l2_ready': 1},
            'expect': {'refill_addr': 0x1000, 'refill_req': 1, 'refill_data': 0xCAFE, 'refill_done': 0, 'busy': 1},
        },
    ]
    return run_verification('L1Refill', l1_refill_cycle, cls, l1_func=None, test_cases=cases, sim_cycles=1)


def test_sfp():
    cls = _l3_class('ifu_sfp', 'SFP')
    cases = [
        {
            'tag': 'sfp_idle',
            'l3_inputs': {'branch_taken': 0, 'branch_mispredict': 0, 'flush_external': 0, 'redirect': 0},
            'l2_inputs': {'branch_taken': 0, 'branch_mispredict': 0, 'flush_external': 0, 'redirect': 0},
            'expect': {'flush': 0, 'flush_redirect': 0, 'spec_depth': 0},
        },
        {
            'tag': 'sfp_branch_taken',
            'l3_inputs': {'branch_taken': 1, 'branch_mispredict': 0, 'flush_external': 0, 'redirect': 0},
            'l2_inputs': {'branch_taken': 1, 'branch_mispredict': 0, 'flush_external': 0, 'redirect': 0},
            'expect': {'flush': 0, 'flush_redirect': 0, 'spec_depth': 7},
        },
        {
            'tag': 'sfp_mispredict',
            'l3_inputs': {'branch_taken': 0, 'branch_mispredict': 1, 'flush_external': 0, 'redirect': 0},
            'l2_inputs': {'branch_taken': 0, 'branch_mispredict': 1, 'flush_external': 0, 'redirect': 0},
            'expect': {'flush': 1, 'flush_redirect': 0, 'spec_depth': 0},
        },
    ]
    return run_verification('SFP', sfp_cycle, cls, l1_func=None, test_cases=cases, sim_cycles=12)


def test_ifu_debug():
    cls = _l3_class('ifu_debug', 'IFUDebug')
    cases = [
        {
            'tag': 'debug_idle',
            'l3_inputs': {'fetch_valid': 0, 'icache_miss': 0, 'branch_taken': 0, 'flush': 0},
            'l2_inputs': {'fetch_valid': 0, 'icache_miss': 0, 'branch_taken': 0, 'flush': 0},
            'expect': {'fetched_instrs': 0, 'icache_misses': 0, 'branches': 0, 'flushes': 0},
        },
        {
            'tag': 'debug_fetch',
            'l3_inputs': {'fetch_valid': 1, 'icache_miss': 0, 'branch_taken': 0, 'flush': 0},
            'l2_inputs': {'fetch_valid': 1, 'icache_miss': 0, 'branch_taken': 0, 'flush': 0},
            'expect': {'fetched_instrs': 10, 'icache_misses': 0, 'branches': 0, 'flushes': 0},
        },
        {
            'tag': 'debug_all_events',
            'l3_inputs': {'fetch_valid': 1, 'icache_miss': 1, 'branch_taken': 1, 'flush': 1},
            'l2_inputs': {'fetch_valid': 1, 'icache_miss': 1, 'branch_taken': 1, 'flush': 1},
            'expect': {'fetched_instrs': 10, 'icache_misses': 10, 'branches': 10, 'flushes': 10},
        },
    ]
    return run_verification('IFUDebug', ifu_debug_cycle, cls, l1_func=None, test_cases=cases)


# =====================================================================
# Main runner
# =====================================================================

def main():
    print('=' * 60)
    print('IFU L2 Cycle-Level Model Verification')
    print('=' * 60)

    tests = [
        ('PCGen', test_pcgen),
        ('BPred', test_bpred),
        ('AddrGen', test_addrgen),
        ('ICacheIF', test_icache_if),
        ('IFCtrl', test_ifctrl),
        ('LBuf', test_lbuf),
        ('IndirectBranchBTB', test_ind_btb),
        ('PreDecodeBuffer', test_predecode),
        ('PCFifo', test_pcfifo),
        ('VectorFetch', test_vec_fetch),
        ('L1Refill', test_l1_refill),
        ('SFP', test_sfp),
        ('IFUDebug', test_ifu_debug),
    ]

    results = {}
    for name, test_fn in tests:
        print(f'\n--- {name} ---')
        ok = test_fn()
        results[name] = 'PASS' if ok else 'FAIL'

    print('\n' + '=' * 60)
    print('Summary')
    print('=' * 60)
    all_pass = True
    for name, status in results.items():
        if status == 'FAIL':
            all_pass = False
        print(f'  {name:25s} {status}')
    print('=' * 60)
    if all_pass:
        print(f'All 13/13 modules PASS')
    else:
        fails = [n for n, s in results.items() if s == 'FAIL']
        print(f'{len(fails)} module(s) FAIL: {", ".join(fails)}')
    print('=' * 60)
    return all_pass


if __name__ == '__main__':
    main()
