"""
test_l2_rtummu — L2 cycle-level model tests for RTU, MMU, CSR, TAGE, OoO modules.
"""
import importlib.util
import sys

sys.path.insert(0, '.')
from rtlgen.forward import LayerVerifier

results = []


def load_l3(path):
    spec = importlib.util.spec_from_file_location('mod', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


from skills.cpu.cycle_level import (
    rob_cycle, commit_unit_cycle, pst_cycle,
    pst_extra_cycle, retire_unit_cycle,
    itlb_cycle, dtlb_cycle, l2tlb_cycle,
    ptw_cycle, mmu_cycle,
    csr_cycle,
    tage_table_cycle, stat_corr_cycle, tage_sc_cycle,
    reservation_station_cycle, dispatch_unit_cycle,
    ooo_core_cycle,
)


# ============================================================
# 1. ROB
# ============================================================
print('--- ROB ---')
m_rob = load_l3('skills/cpu/layer3_dsl/rob.py')
ok = LayerVerifier.verify('ROB', None, m_rob.ROB, [
    {'tag': 'empty', 'l3_inputs': {}, 'expect': {'retire_en': 0, 'full': 0, 'empty': 1}},
    {'tag': 'alloc_one', 'l3_inputs': {'alloc': 1, 'rd_phy': 5, 'complete': 0, 'retire_ready': 0},
     'expect': {'empty': 0, 'full': 0}},
    {'tag': 'alloc_full_cycle', 'l3_inputs': {'alloc': 1, 'rd_phy': 10, 'complete': 1,
                                                'complete_idx': 0, 'retire_ready': 0},
     'expect': {'retire_en': 1, 'retire_rd': 10}},
], l2_func=rob_cycle, sim_cycles=4)
results.append(('ROB', 'PASS' if ok else 'FAIL'))


# ============================================================
# 2. CommitUnit
# ============================================================
print('--- CommitUnit ---')
m2 = load_l3('skills/cpu/layer3_dsl/rtu_commit.py')
ok = LayerVerifier.verify('CommitUnit', None, m2.CommitUnit, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'commit_en': 0}},
    {'tag': 'retire', 'l3_inputs': {'retire_ar': 5, 'retire_pr': 20, 'retire_en': 1},
     'expect': {'commit_ar': 5, 'commit_pr': 20, 'commit_en': 1}},
    {'tag': 'idle', 'l3_inputs': {'retire_en': 0}, 'expect': {'commit_en': 0}},
], l2_func=commit_unit_cycle, sim_cycles=5)
results.append(('CommitUnit', 'PASS' if ok else 'FAIL'))


# ============================================================
# 3. PST
# ============================================================
print('--- PST ---')
m_pst = load_l3('skills/cpu/layer3_dsl/rtu_pst.py')
ok = LayerVerifier.verify('PST', None, m_pst.PST, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'ready_bitmap': 0}},
    {'tag': 'complete_pr5', 'l3_inputs': {'complete_pr': 5, 'complete_en': 1, 'retire_en': 0, 'flush': 0},
     'expect': {'ready_bitmap': 1 << 5}},
    {'tag': 'retire_pr5', 'l3_inputs': {'complete_en': 0, 'retire_pr': 5, 'retire_en': 1, 'flush': 0},
     'expect': {'ready_bitmap': 0}},
], l2_func=pst_cycle, sim_cycles=6)
results.append(('PST', 'PASS' if ok else 'FAIL'))


# ============================================================
# 4. PSTExtra
# ============================================================
print('--- PSTExtra ---')
m3 = load_l3('skills/cpu/layer3_dsl/rtu_pst_extra.py')
ok = LayerVerifier.verify('PSTExtra', None, m3.PSTExtra, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'f_ready': 0, 'v_ready': 0}},
    {'tag': 'complete_fpr3', 'l3_inputs': {'complete_fpr': 3, 'complete_fen': 1, 'retire_fen': 0,
                                             'complete_vpr': 0, 'complete_ven': 0, 'retire_ven': 0, 'flush': 0},
     'expect': {'f_ready': 1 << 3, 'v_ready': 0}},
    {'tag': 'complete_vpr7', 'l3_inputs': {'complete_fpr': 0, 'complete_fen': 0, 'retire_fen': 0,
                                             'complete_vpr': 7, 'complete_ven': 1, 'retire_ven': 0, 'flush': 0},
     'expect': {'f_ready': 0, 'v_ready': 1 << 7}},
    {'tag': 'flush', 'l3_inputs': {'flush': 1}, 'expect': {'f_ready': 0, 'v_ready': 0}},
], l2_func=pst_extra_cycle, sim_cycles=6)
results.append(('PSTExtra', 'PASS' if ok else 'FAIL'))


# ============================================================
# 5. RetireUnit
# ============================================================
print('--- RetireUnit ---')
m4 = load_l3('skills/cpu/layer3_dsl/rtu_retire.py')
ok = LayerVerifier.verify('RetireUnit', None, m4.RetireUnit, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'retire_en': 0, 'flush': 0}},
    {'tag': 'alloc_map', 'l3_inputs': {'alloc_pr': 15, 'alloc_ar': 7, 'alloc_en': 1,
                                        'rob_retire_en': 0, 'rob_empty': 0, 'commit_ready': 1},
     'expect': {'retire_en': 0}},
    {'tag': 'default_lookup', 'l3_inputs': {'alloc_en': 0, 'rob_retire_rd': 15, 'rob_retire_en': 1,
                                             'rob_empty': 0, 'commit_ready': 1},
     'expect': {'retire_ar': 15, 'retire_en': 1, 'retire_pd': 15}},
], l2_func=retire_unit_cycle, sim_cycles=6)
results.append(('RetireUnit', 'PASS' if ok else 'FAIL'))


# ============================================================
# 6. ITLB
# ============================================================
print('--- ITLB ---')
m5 = load_l3('skills/cpu/layer3_dsl/mmu_tlb.py')
ok = LayerVerifier.verify('ITLB', None, m5.ITLB, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'resp_valid': 0, 'resp_miss': 0}},
    {'tag': 'miss', 'l3_inputs': {'req_valid': 1, 'req_vaddr': 0x1000, 'req_asid': 1, 'req_sv39': 1,
                                   'ptw_resp_valid': 0, 'flush': 0, 'flush_asid': 0},
     'expect': {'resp_valid': 0, 'resp_miss': 1, 'ptw_req_valid': 1}},
    {'tag': 'fill_and_hit', 'l3_inputs': {'req_valid': 1, 'req_vaddr': 0x1000, 'req_asid': 1, 'req_sv39': 1,
                                           'ptw_resp_valid': 1, 'ptw_resp_vpn': 1, 'ptw_resp_ppn': 0xABCD,
                                           'ptw_resp_asid': 1, 'ptw_resp_perms': 0x1F, 'ptw_resp_level': 0,
                                           'flush': 0, 'flush_asid': 0},
     'expect': {'resp_valid': 1, 'resp_miss': 0, 'ptw_req_valid': 0}},
], l2_func=itlb_cycle, sim_cycles=6)
results.append(('ITLB', 'PASS' if ok else 'FAIL'))


# ============================================================
# 7. DTLB
# ============================================================
print('--- DTLB ---')
ok = LayerVerifier.verify('DTLB', None, m5.DTLB, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'resp_valid': 0}},
    {'tag': 'miss', 'l3_inputs': {'req_valid': 1, 'req_vaddr': 0x2000, 'req_asid': 2, 'req_sv39': 1,
                                   'req_is_store': 0, 'req_user': 0,
                                   'ptw_resp_valid': 0, 'flush': 0, 'flush_asid': 0},
     'expect': {'resp_miss': 1, 'ptw_req_valid': 1}},
    {'tag': 'fill_and_hit', 'l3_inputs': {'req_valid': 1, 'req_vaddr': 0x2000, 'req_asid': 2, 'req_sv39': 1,
                                           'req_is_store': 0, 'req_user': 0,
                                           'ptw_resp_valid': 1, 'ptw_resp_vpn': 2, 'ptw_resp_ppn': 0xBEEF,
                                           'ptw_resp_asid': 2, 'ptw_resp_perms': 0b00000110,
                                           'ptw_resp_level': 0, 'flush': 0, 'flush_asid': 0},
     'expect': {'resp_valid': 1, 'resp_miss': 0, 'resp_page_fault': 0}},
], l2_func=dtlb_cycle, sim_cycles=6)
results.append(('DTLB', 'PASS' if ok else 'FAIL'))


# ============================================================
# 8. L2TLB
# ============================================================
print('--- L2TLB ---')
m6 = load_l3('skills/cpu/layer3_dsl/mmu_l2tlb.py')
ok = LayerVerifier.verify('L2TLB', None, m6.L2TLB, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'resp_valid': 0, 'resp_hit': 0}},
    {'tag': 'miss', 'l3_inputs': {'req_valid': 1, 'req_vaddr': 0x3000, 'req_asid': 3,
                                   'flush': 0, 'flush_asid': 0, 'ptw_resp_valid': 0},
     'expect': {'resp_hit': 0, 'ptw_req_valid': 1}},
    {'tag': 'refill_and_hit', 'l3_inputs': {'req_valid': 1, 'req_vaddr': 0x3000, 'req_asid': 3,
                                             'flush': 0, 'flush_asid': 0,
                                             'ptw_resp_valid': 1,
                                             'ptw_resp_vpn': 3,
                                             'ptw_resp_ppn': 0xDEAD, 'ptw_resp_asid': 3,
                                             'ptw_resp_perms': 0x1F, 'ptw_resp_level': 2},
     'expect': {'resp_hit': 1, 'ptw_req_valid': 0}},
], l2_func=l2tlb_cycle, sim_cycles=6)
results.append(('L2TLB', 'PASS' if ok else 'FAIL'))


# ============================================================
# 9. PTW
# ============================================================
print('--- PTW ---')
m7 = load_l3('skills/cpu/layer3_dsl/mmu_ptw.py')
ok = LayerVerifier.verify('PTW', None, m7.PTW, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'resp_valid': 0, 'busy': 0}},
    {'tag': 'walk_and_done', 'l3_inputs': {'req_valid': 1, 'req_vaddr': 0x80001000, 'req_asid': 1,
                                            'req_sv39': 1, 'satp_ppn': 0x100,
                                            'mem_resp_valid': 1,
                                            'mem_resp_data': (1 << 1) | 1},
     'expect': {'resp_valid': 1, 'busy': 1}},
], l2_func=ptw_cycle, sim_cycles=8)
results.append(('PTW', 'PASS' if ok else 'FAIL'))


# ============================================================
# 10. MMU
# ============================================================
print('--- MMU ---')
m8 = load_l3('skills/cpu/layer3_dsl/mmu_top.py')
ok = LayerVerifier.verify('MMU', None, m8.MMU, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'ifu_resp_valid': 0, 'lsr_resp_valid': 0, 'busy': 0}},
], l2_func=mmu_cycle, sim_cycles=4)
results.append(('MMU', 'PASS' if ok else 'FAIL'))


# ============================================================
# 11. CSRFile
# ============================================================
print('--- CSRFile ---')
m9 = load_l3('skills/cpu/layer3_dsl/csr.py')
ok = LayerVerifier.verify('CSRFile', None, m9.CSRFile, [
    {'tag': 'read_mvendorid', 'l3_inputs': {'csr_addr': 0xF11, 'csr_op': 0, 'retire_valid': 0},
     'expect': {'csr_rdata': 0x9E4, 'illegal': 0}},
    {'tag': 'write_and_readback', 'l3_inputs': {'csr_addr': 0x300, 'csr_wdata': 0x5, 'csr_op': 1,
                                                  'retire_valid': 0},
     'expect': {'csr_rdata': 0x5, 'illegal': 0}},
    {'tag': 'illegal_addr', 'l3_inputs': {'csr_addr': 0x999, 'csr_op': 0, 'retire_valid': 0},
     'expect': {'illegal': 1}},
], l2_func=csr_cycle, sim_cycles=6)
results.append(('CSRFile', 'PASS' if ok else 'FAIL'))


# ============================================================
# 12. TageTable
# ============================================================
print('--- TageTable ---')
m10 = load_l3('skills/cpu/layer3_dsl/tage.py')
ok = LayerVerifier.verify('TageTable', None, m10.TageTable, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'rd0_ctr': 0, 'rd1_ctr': 0, 'rd0_tag': 0, 'rd1_tag': 0}},
    {'tag': 'write_read_nontag', 'l3_inputs': {'wr_en': 1, 'wr_idx': 5, 'wr_tag': 0, 'wr_ctr': 2, 'wr_ubit': 0,
                                                 'rd0_idx': 5, 'rd1_idx': 0},
     'expect': {'rd0_ctr': 2, 'rd1_ctr': 0}},
], l2_func=tage_table_cycle, sim_cycles=4)
results.append(('TageTable', 'PASS' if ok else 'FAIL'))


# ============================================================
# 13. StatisticalCorrector
# ============================================================
print('--- StatisticalCorrector ---')
ok = LayerVerifier.verify('StatisticalCorrector', None, m10.StatisticalCorrector, [
    {'tag': 'init', 'l3_inputs': {}, 'expect': {'rd0_ctr': 0, 'rd1_ctr': 0}},
    {'tag': 'write_read', 'l3_inputs': {'wr_en': 1, 'wr_idx': 10, 'wr_ctr': 3,
                                          'rd0_idx': 10, 'rd1_idx': 5},
     'expect': {'rd0_ctr': 3, 'rd1_ctr': 0}},
], l2_func=stat_corr_cycle, sim_cycles=4)
results.append(('StatisticalCorrector', 'PASS' if ok else 'FAIL'))


# ============================================================
# 14. TageSC
# ============================================================
print('--- TageSC ---')
ok = LayerVerifier.verify('TageSC', None, m10.TageSC, [
    {'tag': 'init_pred', 'l3_inputs': {'req_pc': 0x1000, 'req_valid': 1, 'global_hist_in': 0,
                                        'upd_valid': 0},
     'expect': {'pred_valid': 1}},
], l2_func=tage_sc_cycle, sim_cycles=4)
results.append(('TageSC', 'PASS' if ok else 'FAIL'))


# ============================================================
# 15. ReservationStation
# ============================================================
print('--- ReservationStation ---')
m11 = load_l3('skills/cpu/layer3_dsl/ooo_issue.py')
ok = LayerVerifier.verify('ReservationStation', None, m11.ReservationStation, [
    {'tag': 'empty', 'l3_inputs': {}, 'expect': {'issue_valid': 0, 'full': 0}},
    {'tag': 'dispatch_prs1_ready', 'l3_inputs': {'dispatch': 1, 'op': 5, 'prs1': 0, 'prs2': 0, 'prd': 7,
                                                  'wakeup_en': 0, 'issue_ready': 1},
     'expect': {'issue_valid': 1, 'issue_op': 5, 'issue_prd': 7}},
], l2_func=reservation_station_cycle, sim_cycles=6)
results.append(('ReservationStation', 'PASS' if ok else 'FAIL'))


# ============================================================
# 16. DispatchUnit
# ============================================================
print('--- DispatchUnit ---')
ok = LayerVerifier.verify('DispatchUnit', None, m11.DispatchUnit, [
    {'tag': 'init', 'l3_inputs': {},
     'expect': {f'dispatch_{i}': 0 for i in range(6)}},
    {'tag': 'slot0', 'l3_inputs': {'slot_valid_0': 1, 'slot_op_0': 3, 'slot_prs1_0': 1, 'slot_prs2_0': 2, 'slot_prd_0': 5,
                                    'rs_full_0': 0},
     'expect': {'dispatch_0': 1, 'dispatch_op_0': 3, 'dispatch_prs1_0': 1, 'dispatch_prs2_0': 2, 'dispatch_prd_0': 5}},
    {'tag': 'blocked', 'l3_inputs': {'slot_valid_0': 1, 'rs_full_0': 1},
     'expect': {'dispatch_0': 0}},
], l2_func=dispatch_unit_cycle, sim_cycles=4)
results.append(('DispatchUnit', 'PASS' if ok else 'FAIL'))


# ============================================================
# 17. OoOCore
# ============================================================
print('--- OoOCore ---')
ok = LayerVerifier.verify('OoOCore', None, m11.OoOCore, [
    {'tag': 'init', 'l3_inputs': {},
     'expect': {f'commit_valid_{i}': 0 for i in range(6)}},
    {'tag': 'dispatch_issue', 'l3_inputs': {'slot_valid_0': 1, 'slot_op_0': 0x12, 'slot_prs1_0': 0, 'slot_prs2_0': 0, 'slot_prd_0': 5,
                                             'slot_valid_1': 0, 'slot_valid_2': 0, 'slot_valid_3': 0, 'slot_valid_4': 0, 'slot_valid_5': 0},
     'expect': {'commit_valid_0': 1, 'commit_prd_0': 5, 'commit_data_0': 0x12}},
], l2_func=ooo_core_cycle, sim_cycles=8)
results.append(('OoOCore', 'PASS' if ok else 'FAIL'))


# ============================================================
# Summary
# ============================================================
print()
print('=' * 60)
print('Cross-Layer Verification Summary (RTU/MMU/CSR/TAGE/OoO)')
print('=' * 60)
for name, status in results:
    print(f'  {name:25s}: {status}')
print('=' * 60)
passed = sum(1 for _, s in results if s == 'PASS')
total = len(results)
print(f'  TOTAL: {passed}/{total} PASS')

if passed == total:
    print('ALL PASS')
else:
    print(f'{total - passed} FAILURES')
    sys.exit(1)
