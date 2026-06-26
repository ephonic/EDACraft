"""
test_l2_idu — L2 cycle-level model tests for all 14 IDU modules.
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
    decoder_cycle, ir_ctrl_cycle, is_ctrl_cycle,
    sdiq_cycle, viq_cycle,
    rf_write_ctrl_cycle, rf_read_ctrl_cycle,
    prf_cycle, fwd_net_cycle, fence_unit_cycle,
    f_rename_table_cycle, v_rename_table_cycle,
    rename_table_cycle, issue_queue_cycle,
)


# ============================================================
# 1. Decoder
# ============================================================
print('--- Decoder ---')
m = load_l3('skills/cpu/layer3_dsl/idu_decode.py')
ok = LayerVerifier.verify('Decoder', None, m.Decoder, [
    {'tag': 'addi', 'l3_inputs': {'instr': 0x00000013}, 'expect': {'opcode': 0x13, 'rd': 0, 'rs1': 0, 'funct3': 0, 'is_imm': 1}},
    {'tag': 'add',  'l3_inputs': {'instr': 0x00000033}, 'expect': {'opcode': 0x33, 'funct7': 0, 'is_imm': 0}},
    {'tag': 'addi_imm', 'l3_inputs': {'instr': (0x100 << 20) | (2 << 15) | (0 << 12) | (1 << 7) | 0x13},
     'expect': {'opcode': 0x13, 'rd': 1, 'rs1': 2, 'imm': 0x100, 'is_imm': 1}},
    {'tag': 'lui', 'l3_inputs': {'instr': (0x12345 << 12) | 0x37},
     'expect': {'opcode': 0x37, 'rd': 0, 'imm': 0x12345000}},
], l2_func=decoder_cycle, sim_cycles=5)
results.append(('Decoder', 'PASS' if ok else 'FAIL'))


# ============================================================
# 2. IRCtrl
# ============================================================
print('--- IRCtrl ---')
m = load_l3('skills/cpu/layer3_dsl/idu_ir_ctrl.py')
ok = LayerVerifier.verify('IRCtrl', None, m.IRCtrl, [
    {'tag': 'no_req',      'l3_inputs': {'alloc_req': 0, 'freelist_empty': 0}, 'expect': {'alloc_grant': 0, 'stall': 0}},
    {'tag': 'grant',       'l3_inputs': {'alloc_req': 1, 'freelist_empty': 0}, 'expect': {'alloc_grant': 1, 'stall': 0}},
    {'tag': 'stall',       'l3_inputs': {'alloc_req': 1, 'freelist_empty': 1}, 'expect': {'alloc_grant': 0, 'stall': 1}},
    {'tag': 'no_req_empty','l3_inputs': {'alloc_req': 0, 'freelist_empty': 1}, 'expect': {'alloc_grant': 0, 'stall': 0}},
], l2_func=ir_ctrl_cycle, sim_cycles=5)
results.append(('IRCtrl', 'PASS' if ok else 'FAIL'))


# ============================================================
# 3. ISCtrl
# ============================================================
print('--- ISCtrl ---')
m = load_l3('skills/cpu/layer3_dsl/idu_is_ctrl.py')
ok = LayerVerifier.verify('ISCtrl', None, m.ISCtrl, [
    {'tag': 'no_ready',    'l3_inputs': {'ready_mask': 0, 'grant_any': 1}, 'expect': {'grant_valid': 0}},
    {'tag': 'grant_any_0', 'l3_inputs': {'ready_mask': 0xF, 'grant_any': 0}, 'expect': {'grant_valid': 0, 'grant_idx': 0}},
    {'tag': 'bit0_ready',  'l3_inputs': {'ready_mask': 0b0001, 'grant_any': 1}, 'expect': {'grant_valid': 1}},
    {'tag': 'bit1_ready',  'l3_inputs': {'ready_mask': 0b0010, 'grant_any': 1}, 'expect': {'grant_valid': 1}},
    {'tag': 'all_ready',   'l3_inputs': {'ready_mask': 0b1111, 'grant_any': 1}, 'expect': {'grant_valid': 1}},
], l2_func=is_ctrl_cycle, sim_cycles=5)
results.append(('ISCtrl', 'PASS' if ok else 'FAIL'))


# ============================================================
# 4. SDIQ
# ============================================================
print('--- SDIQ ---')
m = load_l3('skills/cpu/layer3_dsl/idu_issue_extra.py')
ok = LayerVerifier.verify('SDIQ', None, m.SDIQ, [
    {'tag': 'init_empty','l3_inputs': {}, 'expect': {'issue_valid': 0, 'full': 0}},
], l2_func=sdiq_cycle, sim_cycles=5)
results.append(('SDIQ', 'PASS' if ok else 'FAIL'))


# ============================================================
# 5. VIQ
# ============================================================
print('--- VIQ ---')
ok = LayerVerifier.verify('VIQ', None, m.VIQ, [
    {'tag': 'init_empty','l3_inputs': {}, 'expect': {'issue_valid': 0, 'full': 0}},
], l2_func=viq_cycle, sim_cycles=5)
results.append(('VIQ', 'PASS' if ok else 'FAIL'))


# ============================================================
# 6. RFWriteCtrl
# ============================================================
print('--- RFWriteCtrl ---')
m2 = load_l3('skills/cpu/layer3_dsl/idu_rf_ctrl.py')
ok = LayerVerifier.verify('RFWriteCtrl', None, m2.RFWriteCtrl, [
    {'tag': 'ready_no_busy','l3_inputs': {'busy': 0, 'we': 0, 'pr_waddr': 0, 'pr_wdata': 0}, 'expect': {'ready': 1}},
    {'tag': 'busy_stall',  'l3_inputs': {'busy': 1, 'we': 0, 'pr_waddr': 0, 'pr_wdata': 0}, 'expect': {'ready': 0}},
], l2_func=rf_write_ctrl_cycle, sim_cycles=5)
results.append(('RFWriteCtrl', 'PASS' if ok else 'FAIL'))


# ============================================================
# 7. RFReadCtrl
# ============================================================
print('--- RFReadCtrl ---')
ok = LayerVerifier.verify('RFReadCtrl', None, m2.RFReadCtrl, [
    {'tag': 'fwd_match', 'l3_inputs': {'pr_addr1': 5, 'pr_addr2': 6, 'pr_waddr': 5, 'pr_wdata': 0x1234, 'pr_we': 1},
     'expect': {'rdata1': 0x1234, 'rdata2': 0}},
    {'tag': 'fwd_pr0',   'l3_inputs': {'pr_addr1': 0, 'pr_addr2': 5, 'pr_waddr': 0, 'pr_wdata': 0xFFFF, 'pr_we': 1},
     'expect': {'rdata1': 0}},
    {'tag': 'no_fwd',    'l3_inputs': {'pr_addr1': 7, 'pr_addr2': 8, 'pr_waddr': 5, 'pr_wdata': 0x5678, 'pr_we': 1},
     'expect': {'rdata1': 0, 'rdata2': 0}},
], l2_func=rf_read_ctrl_cycle, sim_cycles=5)
results.append(('RFReadCtrl', 'PASS' if ok else 'FAIL'))


# ============================================================
# 8. PRF
# ============================================================
print('--- PRF ---')
m3 = load_l3('skills/cpu/layer3_dsl/idu_rf_pregfile.py')
ok = LayerVerifier.verify('PRF', None, m3.PRF, [
    {'tag': 'pr0_read',    'l3_inputs': {'rd_addr1': 0, 'rd_addr2': 0}, 'expect': {'rd_data1': 0, 'rd_data2': 0}},
    {'tag': 'wr_rd_pr5',   'l3_inputs': {'wr_en': 1, 'wr_addr': 5, 'wr_data': 0xABCD, 'rd_addr1': 5, 'rd_addr2': 5},
     'expect': {'rd_data1': 0xABCD, 'rd_data2': 0xABCD}},
    {'tag': 'wr_pr0_ignored','l3_inputs': {'wr_en': 1, 'wr_addr': 0, 'wr_data': 0xFFFF, 'rd_addr1': 0},
     'expect': {'rd_data1': 0}},
], l2_func=prf_cycle, sim_cycles=5)
results.append(('PRF', 'PASS' if ok else 'FAIL'))


# ============================================================
# 9. FwdNet
# ============================================================
print('--- FwdNet ---')
m4 = load_l3('skills/cpu/layer3_dsl/idu_rf_fwd.py')
ok = LayerVerifier.verify('FwdNet', None, m4.FwdNet, [
    {'tag': 'raw_pass',    'l3_inputs': {'rd_addr1': 10, 'rd_data1_raw': 0xAA, 'rd_addr2': 11, 'rd_data2_raw': 0xBB,
                                          'fwd0_en': 0, 'fwd1_en': 0, 'fwd0_addr': 0, 'fwd0_data': 0, 'fwd1_addr': 0, 'fwd1_data': 0},
     'expect': {'rd_data1': 0xAA, 'rd_data2': 0xBB}},
    {'tag': 'fwd0_match',  'l3_inputs': {'rd_addr1': 10, 'rd_data1_raw': 0xAA, 'fwd0_en': 1, 'fwd0_addr': 10, 'fwd0_data': 0x123,
                                          'fwd1_en': 0, 'rd_addr2': 0, 'rd_data2_raw': 0, 'fwd1_addr': 0, 'fwd1_data': 0},
     'expect': {'rd_data1': 0x123}},
    {'tag': 'fwd1_match',  'l3_inputs': {'rd_addr2': 12, 'rd_data2_raw': 0xBB, 'fwd1_en': 1, 'fwd1_addr': 12, 'fwd1_data': 0x456,
                                          'fwd0_en': 0, 'rd_addr1': 0, 'rd_data1_raw': 0, 'fwd0_addr': 0, 'fwd0_data': 0, 'fwd1_addr': 12, 'fwd1_data': 0x456},
     'expect': {'rd_data2': 0x456}},
    {'tag': 'fwd0_prio',   'l3_inputs': {'rd_addr1': 20, 'rd_data1_raw': 0xAA, 'fwd0_en': 1, 'fwd0_addr': 20, 'fwd0_data': 0xAAA,
                                          'fwd1_en': 1, 'fwd1_addr': 20, 'fwd1_data': 0xBBB, 'rd_addr2': 0, 'rd_data2_raw': 0},
     'expect': {'rd_data1': 0xAAA}},
    {'tag': 'pr0_zero',    'l3_inputs': {'rd_addr1': 0, 'rd_data1_raw': 0xBEEF, 'fwd0_en': 1, 'fwd0_addr': 0, 'fwd0_data': 0xDEAD,
                                          'fwd1_en': 0, 'rd_addr2': 0, 'rd_data2_raw': 0, 'fwd1_addr': 0, 'fwd1_data': 0},
     'expect': {'rd_data1': 0}},
], l2_func=fwd_net_cycle, sim_cycles=5)
results.append(('FwdNet', 'PASS' if ok else 'FAIL'))


# ============================================================
# 10. FenceUnit
# ============================================================
print('--- FenceUnit ---')
m5 = load_l3('skills/cpu/layer3_dsl/idu_fence.py')
ok = LayerVerifier.verify('FenceUnit', None, m5.FenceUnit, [
    {'tag': 'idle',        'l3_inputs': {'enqueue': 0}, 'expect': {'busy': 0, 'store_drain_req': 0, 'icache_flush_req': 0, 'completed': 0}},
    {'tag': 'fence_start', 'l3_inputs': {'enqueue': 1, 'is_fence_i': 0, 'store_buffer_drain': 0},
     'expect': {'busy': 1, 'store_drain_req': 1, 'icache_flush_req': 0, 'completed': 0}},
], l2_func=fence_unit_cycle, sim_cycles=5)
results.append(('FenceUnit', 'PASS' if ok else 'FAIL'))


# ============================================================
# 11. FRenameTable
# ============================================================
print('--- FRenameTable ---')
m6 = load_l3('skills/cpu/layer3_dsl/idu_ir_frt.py')
ok = LayerVerifier.verify('FRenameTable', None, m6.FRenameTable, [
    {'tag': 'read_init', 'l3_inputs': {'frs1': 0, 'frs2': 1}, 'expect': {'pfrs1': 0, 'pfrs2': 1}},
    {'tag': 'wr_remap',  'l3_inputs': {'frd': 5, 'frd_phy': 10, 'frd_we': 1, 'frs1': 5},
     'expect': {'pfrs1': 10}},
], l2_func=f_rename_table_cycle, sim_cycles=5)
results.append(('FRenameTable', 'PASS' if ok else 'FAIL'))


# ============================================================
# 12. VRenameTable
# ============================================================
print('--- VRenameTable ---')
m7 = load_l3('skills/cpu/layer3_dsl/idu_ir_vrt.py')
ok = LayerVerifier.verify('VRenameTable', None, m7.VRenameTable, [
    {'tag': 'read_init', 'l3_inputs': {'vrs1': 0, 'vrs2': 1}, 'expect': {'pvrs1': 0, 'pvrs2': 1}},
    {'tag': 'wr_remap',  'l3_inputs': {'vrd': 3, 'vrd_phy': 7, 'vrd_we': 1, 'vrs1': 3},
     'expect': {'pvrs1': 7}},
], l2_func=v_rename_table_cycle, sim_cycles=5)
results.append(('VRenameTable', 'PASS' if ok else 'FAIL'))


# ============================================================
# 13. RenameTable
# ============================================================
print('--- RenameTable ---')
m8 = load_l3('skills/cpu/layer3_dsl/rename.py')
ok = LayerVerifier.verify('RenameTable', None, m8.RenameTable, [
    {'tag': 'read_init', 'l3_inputs': {'rs1': 0, 'rs2': 1}, 'expect': {'prs1': 0, 'prs2': 1}},
    {'tag': 'wr_remap',  'l3_inputs': {'rd': 5, 'rd_phy': 20, 'rd_we': 1, 'rs1': 5},
     'expect': {'prs1': 20}},
], l2_func=rename_table_cycle, sim_cycles=5)
results.append(('RenameTable', 'PASS' if ok else 'FAIL'))


# ============================================================
# 14. IssueQueue
# ============================================================
print('--- IssueQueue ---')
m9 = load_l3('skills/cpu/layer3_dsl/issue_queue.py')
ok = LayerVerifier.verify('IssueQueue', None, m9.IssueQueue, [
    {'tag': 'init_empty', 'l3_inputs': {}, 'expect': {'issue_valid': 0, 'full': 0, 'issue_op': 0, 'issue_prd': 0}},
], l2_func=issue_queue_cycle, sim_cycles=5)
results.append(('IssueQueue', 'PASS' if ok else 'FAIL'))


# ============================================================
# Summary
# ============================================================
print()
print('=' * 60)
print('IDU L2 Cycle-Level Model Test Summary')
print('=' * 60)
for name, status in results:
    print(f'  {name:20s}: {status}')
print('=' * 60)
passed = sum(1 for _, s in results if s == 'PASS')
total = len(results)
print(f'  TOTAL: {passed}/{total} PASS')

if passed == total:
    print('ALL PASS')
else:
    print(f'{total - passed} FAILURES')
    sys.exit(1)
