"""
rtlgen.arch_skel — Architecture Skeleton Generator

Generates AgentPackage bundles from ArchDefinition:
  - DSL Module skeleton with ports, state variables, and TODO comments
  - Golden test vectors from behavioral reference
  - Implementation steps based on PE type and metadata
  - Interconnect interface definition

Template categories (PE type → skeleton template):
  CPU:    ifu, idu, alu, lsu, rtu/rob, regfile, cache
  GPGPU:  cta_scheduler, warp_scheduler, sm_wrapper, pipe, pc_control,
          shared_mem, icache, dcache, arbiter, pop_cnt
  Memory: memory_controller, dfi_sequencer
  Generic: generic

GPGPU patterns from reference RTL:
  - Generate-loop patterns (per-warp pc_control, per-SM sm_wrapper)
  - Valid/ready handshake interface generation
  - Sub-module decomposition (cta_scheduler → 5 sub-modules)
  - Barrier synchronization state machines
  - Resource tracking (VGPR/SGPR/LDS allocation)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rtlgen.arch_def import (
    AgentPackage,
    ArchDefinition,
    CycleContext,
    ProcessingElement,
    StateDesc,
)
from rtlgen.core import Module, Input, Output, Wire, Reg, Array, SubmoduleInst, Const

try:
    from rtlgen.skill_retriever import SkillRetriever, RetrievalQuery
    from rtlgen.logic_generator import LogicGenerator, LogicGenerationResult
    from rtlgen.verifier import Verifier, VerificationResult
    _SKILL_GUIDANCE_AVAILABLE = True
except ImportError:
    _SKILL_GUIDANCE_AVAILABLE = False

try:
    from rtlgen.gen_requirement import (
        ModuleRequirement, ReferenceSummary, GenerationContext,
        TaskGenerationContext,
    )
    from rtlgen.behavior_extract import extract_behavior_requirements
    from rtlgen.reference_extractor import ReferenceExtractor
    _GEN_REQUIREMENT_AVAILABLE = True
except ImportError:
    _GEN_REQUIREMENT_AVAILABLE = False
    ModuleRequirement = None
    ReferenceSummary = None
    GenerationContext = None
    TaskGenerationContext = None
    extract_behavior_requirements = None
    ReferenceExtractor = None


# Default signal widths for common RTL signal names used in skeleton templates.
# Used as fallback when parent PE ports don't define a width.
_DEFAULT_SIGNAL_WIDTHS: Dict[str, int] = {
    # Addresses & data
    "icache_rdata": 64, "icache_addr": 64,
    "dcache_rdata": 64, "dcache_addr": 64, "dcache_wdata": 64,
    "fetch_instr": 32, "fetch_pc": 64,
    "decode_instr": 32, "decode_pc": 64,
    "exec_instr": 32, "exec_pc": 64,
    "branch_target": 64, "branch_taken": 1,
    "dec_ra": 64, "dec_rb": 64, "dec_rd": 64,
    "imm_i": 12, "imm_s": 12, "imm_b": 13, "imm_u": 20, "imm_j": 21,
    "exec_alu_result": 64, "mem_alu_result": 64,
    "wb_result": 64, "wb_fwd_result": 64,
    "mem_load_data": 64,
    # Register indices
    "rs1": 5, "rs2": 5, "rd": 5,
    "wb_rd": 5, "mem_rd": 5, "exec_rd": 5, "wb_fwd_rd": 5,
    # Opcode / funct
    "opcode": 7, "funct3": 3, "funct7": 7,
    # Misc
    "retire_count": 3,
    # Cache
    "tag_in": 64, "tag_rdata": 64, "tag_wdata": 64,
    "data_rdata": 64, "data_wdata": 64,
    "rdata": 64, "addr": 64, "wdata": 64,
    "fill_data": 64, "miss_addr": 64,
    # NoC / mesh
    "e_flit": 64, "w_flit": 64, "n_flit": 64, "s_flit": 64, "loc_inj_flit": 64,
    "e_flit_o": 64, "w_flit_o": 64, "n_flit_o": 64, "s_flit_o": 64, "loc_ej_flit": 64,
    "x_pos": 3, "y_pos": 3,
    # Coherence
    "probe_addr": 64, "writeback_data": 64, "writeback_core_id": 6,
    "req_addr": 64, "resp_action": 3,
    # Common data paths (not covered above)
    "alu_result": 64, "result": 64, "alu_out": 64,
    "mem_result": 64, "exec_result": 64,
    "din": 64, "dout": 64, "data": 64, "din_val": 64,
    "flit": 64, "e_flit_in": 64, "w_flit_in": 64,
    "n_flit_in": 64, "s_flit_in": 64,
    "grant_e": 1, "grant_w": 1, "grant_n": 1, "grant_s": 1, "grant_j": 1,
    "route_e": 1, "route_w": 1, "route_n": 1, "route_s": 1, "route_j": 1,
    "pop_e": 1, "pop_w": 1, "pop_n": 1, "pop_s": 1, "pop_j": 1,
    # Common control / handshake signals (1-bit)
    "valid": 1, "ready": 1, "fire": 1, "done": 1,
    "stall": 1, "flush": 1,
    "req": 1, "rsp": 1, "ack": 1,
    "hit": 1, "miss": 1,
    "core_stall": 1, "core_halted": 1,
    "icache_req": 1, "icache_ready": 1, "icache_valid": 1,
    "dcache_req": 1, "dcache_ready": 1, "dcache_valid": 1, "dcache_wen": 1,
    "fetch_valid": 1, "decode_valid": 1, "exec_valid": 1,
    "mem_valid": 1, "wb_valid": 1,
    "wb_fwd_valid": 1, "wb_fwd_valid": 1,
    "retire_valid": 1,
    "noc_req": 1, "noc_ready": 1, "noc_valid": 1,
    "snoop_req": 1, "snoop_ack": 1,
    "resp_valid": 1, "req_valid": 1,
    "e_valid": 1, "w_valid": 1, "n_valid": 1, "s_valid": 1, "j_valid": 1,
    "e_valid_in": 1, "w_valid_in": 1, "n_valid_in": 1, "s_valid_in": 1,
    "e_valid_o": 1, "w_valid_o": 1, "n_valid_o": 1, "s_valid_o": 1, "loc_ej_valid": 1,
    "e_ready": 1, "w_ready": 1, "n_ready": 1, "s_ready": 1, "j_ready": 1,
    "e_ready_in": 1, "w_ready_in": 1, "n_ready_in": 1, "s_ready_in": 1,
    "dir_state": 3, "dir_sharers": 32,
    "update_state": 3, "update_sharers": 32,
    "snoop_addr": 64, "snoop_data": 64,
    "tag_write": 1, "data_write": 1,
    "index": 8, "offset": 8,
    "pc": 64, "next_pc": 64,
    "instr": 32, "instruction": 32,
    "core_id": 6, "tile_id": 6,
    "flush_target": 64, "redirect": 1,
    "stall": 1, "mem_stall": 1,
    "exec_mem_req": 1, "exec_mem_wen": 1,
    "exec_mem_addr": 64, "exec_mem_wdata": 64,
}

# Suffix/prefix patterns for width inference when signal name is not in _DEFAULT_SIGNAL_WIDTHS
# Ordered so longer/more-specific patterns come before shorter ones (e.g., "rdata" before "data")
_WIDTH_PATTERNS_DATA_64 = ("_rdata", "_wdata", "_addr", "_result", "_flit", "_din", "_dout",
                           "_target", "_pc", "_state", "_rdata_o", "_wdata_o", "_addr_o",
                           "rdata", "wdata", "addr", "result", "flit", "target", "rdata_o", "wdata_o")
_WIDTH_PATTERNS_DATA_32 = ("_instr", "instr", "pc")
_WIDTH_PATTERNS_BIT = ("_valid", "_ready", "_fire", "_req", "_ack", "_wen", "_en", "_hit", "_miss",
                       "_stall", "_flush", "_done", "_redirect", "_taken", "_grant", "_pop",
                       "_write", "_read", "_o_valid", "_i_valid", "_o_ready", "_i_ready",
                       "valid", "ready", "fire", "req", "ack", "wen", "hit", "miss",
                       "stall", "flush", "done", "redirect", "taken", "grant", "pop",
                       "write", "read", "o_valid", "i_valid", "o_ready", "i_ready")


def _infer_signal_width(name: str) -> int:
    """Infer signal width from name patterns when not found in _DEFAULT_SIGNAL_WIDTHS."""
    name_lower = name.lower()
    # Check data-width patterns first (64-bit)
    for pat in _WIDTH_PATTERNS_DATA_64:
        if name_lower.endswith(pat) or pat in name_lower:
            return 64
    # Check 32-bit patterns
    for pat in _WIDTH_PATTERNS_DATA_32:
        if name_lower.endswith(pat) or pat in name_lower:
            return 32
    # Check 1-bit patterns
    for pat in _WIDTH_PATTERNS_BIT:
        if name_lower.endswith(pat) or pat in name_lower:
            return 1
    # Default: unknown signals are 32-bit (safer than 1-bit for internal wires)
    return 32


# =====================================================================
# Skeleton Templates by PE Type
# =====================================================================

class _TemplateContext:
    """Template execution context for skeleton generation."""

    def __init__(self, pe: ProcessingElement, arch: ArchDefinition):
        self.pe = pe
        self.arch = arch
        self.module: Optional[Module] = None


def _create_base_module(pe: ProcessingElement) -> Module:
    """创建带端口声明的基础 DSL Module。

    If the PE type has sub-module decomposition defined, creates a
    hierarchical module with sub-module instantiations and interconnect wires.
    """
    # Check if PE type has sub-module decomposition
    submod_def = _SUBMODULE_DEFS.get(pe.pe_type)
    if submod_def is not None:
        return _create_hierarchical_base_module(pe, submod_def)

    module = Module(pe.name)
    module._type_name = pe.name  # Override class name with PE name
    # Clock and reset
    module.clk = Input(1, "clk")
    module.rst_n = Input(1, "rst_n")
    # Data ports
    for port in pe.inputs:
        setattr(module, port.name, Input(port.width, port.name))
    for port in pe.outputs:
        setattr(module, port.name, Output(port.width, port.name))
    return module


# =====================================================================
# Sub-Module Decomposition Templates
# =====================================================================
# Define the sub-module hierarchy for each PE type. These templates
# specify what sub-modules a PE should contain, their interfaces, and
# how they connect. Agents fill in detailed logic for each sub-module.

_SUBMODULE_DEFS: Dict[str, dict] = {
    "ifu": {
        "submodules": [
            {"name": "addrgen", "type": "ct_ifu_addrgen",
             "description": "ct_ifu_addrgen (19 inputs, 17 outputs)",
             "inputs": ["cp0_ifu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["addrgen_btb_index[9:0]", "addrgen_btb_tag[9:0]", "addrgen_btb_target_pc[19:0]", "addrgen_btb_update_vld"]},
            {"name": "bht", "type": "ct_ifu_bht",
             "description": "Branch history table: gshare predictor with 4096-entry PHT, history register XOR hash (37 inputs, 12 outputs)",
             "inputs": ["cp0_ifu_bht_en", "cp0_ifu_icg_en", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["bht_ifctrl_inv_done", "bht_ifctrl_inv_on", "bht_ind_btb_rtu_ghr[7:0]", "bht_ind_btb_vghr[7:0]"]},
            {"name": "btb", "type": "ct_ifu_btb",
             "description": "Branch target buffer: 1024-entry 4-way set-associative, tag+target+valid storage (25 inputs, 18 outputs)",
             "inputs": ["addrgen_btb_index[9:0]", "addrgen_btb_tag[9:0]", "addrgen_btb_target_pc[19:0]", "addrgen_btb_update_vld"],
             "outputs": ["btb_ifctrl_inv_done", "btb_ifctrl_inv_on", "btb_ifdp_way0_pred[1:0]", "btb_ifdp_way0_tag[9:0]"]},
            {"name": "l0_btb", "type": "ct_ifu_l0_btb",
             "description": "L0 branch target buffer: 4-entry single-cycle BTB for fastest branch resolution (34 inputs, 12 outputs)",
             "inputs": ["addrgen_l0_btb_update_entry[15:0]", "addrgen_l0_btb_update_vld", "addrgen_l0_btb_update_vld_bit", "addrgen_l0_btb_wen[3:0]"],
             "outputs": ["l0_btb_debug_cur_state[1:0]", "l0_btb_ibdp_entry_fifo[15:0]", "l0_btb_ifctrl_chgflw_pc[38:0]", "l0_btb_ifctrl_chgflw_way_pred[1:0]"]},
            {"name": "sfp", "type": "ct_ifu_sfp",
             "description": "Static/fixed-length prediction: loop buffer for short backward branches (34 inputs, 3 outputs)",
             "inputs": ["cp0_ifu_icg_en", "cp0_ifu_nsfe", "cp0_ifu_vsetvli_pred_disable", "cp0_ifu_vsetvli_pred_mode"],
             "outputs": ["sfp_ifdp_hit_pc_lo[2:0]", "sfp_ifdp_hit_type[3:0]", "sfp_ifdp_pc_hit"]},
            {"name": "ibctrl", "type": "ct_ifu_ibctrl",
             "description": "Instruction buffer control: manage ibuf fill/empty, stall generation, bypass (52 inputs, 65 outputs)",
             "inputs": ["addrgen_ibctrl_cancel", "cp0_ifu_icg_en", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["ibctrl_debug_buf_stall", "ibctrl_debug_bypass_inst_vld", "ibctrl_debug_fifo_full_stall", "ibctrl_debug_fifo_stall"]},
            {"name": "ibdp", "type": "ct_ifu_ibdp",
             "description": "Instruction buffer datapath: split/align instructions from ibuf to decode (306 inputs, 221 outputs)",
             "inputs": ["cp0_ifu_icg_en", "cp0_ifu_ras_en", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["ibdp_addrgen_branch_base[38:0]", "ibdp_addrgen_branch_offset[20:0]", "ibdp_addrgen_branch_result[38:0]", "ibdp_addrgen_branch_valid"]},
            {"name": "ibuf", "type": "ct_ifu_ibuf",
             "description": "Instruction buffer: 8-entry fetch buffer storing fetched cache lines (89 inputs, 105 outputs)",
             "inputs": ["cp0_ifu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["ibuf_ibctrl_empty", "ibuf_ibctrl_stall", "ibuf_ibdp_bypass_inst0[31:0]", "ibuf_ibdp_bypass_inst0_bkpta"]},
            {"name": "icache_if", "type": "ct_ifu_icache_if",
             "description": "I-cache interface: request generation, line buffer, tag/data return (41 inputs, 15 outputs)",
             "inputs": ["cp0_ifu_icache_en", "cp0_ifu_icg_en", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["icache_if_ifctrl_inst_data0[127:0]", "icache_if_ifctrl_inst_data1[127:0]", "icache_if_ifctrl_tag_data0[28:0]", "icache_if_ifctrl_tag_data1[28:0]"]},
            {"name": "ifctrl", "type": "ct_ifu_ifctrl",
             "description": "Fetch control: overall IFU pipeline control, stall, flush, redirect (56 inputs, 56 outputs)",
             "inputs": ["bht_ifctrl_inv_done", "bht_ifctrl_inv_on", "btb_ifctrl_inv_done", "btb_ifctrl_inv_on"],
             "outputs": ["ifctrl_bht_inv", "ifctrl_bht_pipedown", "ifctrl_bht_stall", "ifctrl_btb_inv"]},
            {"name": "ifdp", "type": "ct_ifu_ifdp",
             "description": "Fetch datapath: PC selection, branch prediction integration, instruction stream (81 inputs, 133 outputs)",
             "inputs": ["btb_ifdp_way0_pred[1:0]", "btb_ifdp_way0_tag[9:0]", "btb_ifdp_way0_target[19:0]", "btb_ifdp_way0_vld"],
             "outputs": ["ifdp_debug_acc_err_vld", "ifdp_debug_mmu_expt_vld", "ifdp_ipctrl_expt_vld", "ifdp_ipctrl_expt_vld_dup"]},
            {"name": "ind_btb", "type": "ct_ifu_ind_btb",
             "description": "Indirect BTB: indirect branch target cache for JR/JALR predictions (25 inputs, 4 outputs)",
             "inputs": ["bht_ind_btb_rtu_ghr[7:0]", "bht_ind_btb_vghr[7:0]", "cp0_ifu_icg_en", "cp0_ifu_ind_btb_en"],
             "outputs": ["ind_btb_ibctrl_dout[22:0]", "ind_btb_ibctrl_priv_mode[1:0]", "ind_btb_ifctrl_inv_done", "ind_btb_ifctrl_inv_on"]},
            {"name": "ipb", "type": "ct_ifu_ipb",
             "description": "I-cache prefetch buffer: prefetch engine for I-cache miss handling (32 inputs, 23 outputs)",
             "inputs": ["biu_ifu_rd_data[127:0]", "biu_ifu_rd_data_vld", "biu_ifu_rd_grnt", "biu_ifu_rd_id"],
             "outputs": ["ifu_biu_r_ready", "ifu_biu_rd_addr[39:0]", "ifu_biu_rd_burst[1:0]", "ifu_biu_rd_cache[3:0]"]},
            {"name": "ipctrl", "type": "ct_ifu_ipctrl",
             "description": "Instruction prefetch control: prefetch FSM, stream detection (83 inputs, 94 outputs)",
             "inputs": ["cp0_ifu_bht_en", "cp0_ifu_no_op_req", "cpurst_b", "forever_cpuclk"],
             "outputs": ["ipctrl_bht_con_br_gateclk_en", "ipctrl_bht_con_br_taken", "ipctrl_bht_con_br_vld", "ipctrl_bht_more_br"]},
            {"name": "ipdp", "type": "ct_ifu_ipdp",
             "description": "Instruction prefetch datapath: prefetch address generation, stream tracking (156 inputs, 187 outputs)",
             "inputs": ["addrgen_ipdp_chgflw_vl[7:0]", "addrgen_ipdp_chgflw_vlmul[1:0]", "addrgen_ipdp_chgflw_vsew[2:0]", "addrgen_xx_pcload"],
             "outputs": ["ipdp_bht_h0_con_br", "ipdp_bht_vpc[38:0]", "ipdp_btb_index_pc[38:0]", "ipdp_btb_target_pc[19:0]"]},
            {"name": "l1_refill", "type": "ct_ifu_l1_refill",
             "description": "L1 I-cache refill: miss handling FSM, bus request generation (27 inputs, 39 outputs)",
             "inputs": ["cp0_ifu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["ifu_hpcp_icache_miss_pre", "l1_refill_debug_refill_st[3:0]", "l1_refill_icache_if_fifo", "l1_refill_icache_if_first"]},
            {"name": "lbuf", "type": "ct_ifu_lbuf",
             "description": "Line buffer: stores fetched cache lines before ibuf extraction (106 inputs, 63 outputs)",
             "inputs": ["bht_lbuf_pre_ntaken_result[31:0]", "bht_lbuf_pre_taken_result[31:0]", "bht_lbuf_vghr[21:0]", "cp0_ifu_icg_en"],
             "outputs": ["lbuf_addrgen_active_state", "lbuf_addrgen_cache_state", "lbuf_addrgen_chgflw_mask", "lbuf_bht_active_state"]},
            {"name": "pcfifo_if", "type": "ct_ifu_pcfifo_if",
             "description": "PC FIFO interface: FIFO of fetch PCs sent to execute for branch tracking (31 inputs, 22 outputs)",
             "inputs": ["ibctrl_pcfifo_if_create_vld", "ibctrl_pcfifo_if_ind_btb_miss", "ibctrl_pcfifo_if_ind_target_pc[38:0]", "ibctrl_pcfifo_if_ras_target_pc[38:0]"],
             "outputs": ["ifu_iu_pcfifo_create0_bht_pred", "ifu_iu_pcfifo_create0_chk_idx[24:0]", "ifu_iu_pcfifo_create0_cur_pc[39:0]", "ifu_iu_pcfifo_create0_dst_vld"]},
            {"name": "pcgen", "type": "ct_ifu_pcgen",
             "description": "PC generation with L0 BTB fast path, branch redirect, sequential PC+4/PC+8 (49 inputs, 55 outputs)",
             "inputs": ["addrgen_pcgen_pc[38:0]", "addrgen_pcgen_pcload", "cp0_ifu_icg_en", "cp0_ifu_iwpe"],
             "outputs": ["ifu_mmu_abort", "ifu_mmu_va[62:0]", "ifu_mmu_va_vld", "ifu_rtu_cur_pc[38:0]"]},
            {"name": "ras", "type": "ct_ifu_ras",
             "description": "Return address stack: 8-entry LIFO for JALR return address prediction (18 inputs, 5 outputs)",
             "inputs": ["cp0_ifu_icg_en", "cp0_ifu_ras_en", "cp0_yy_clk_en", "cp0_yy_priv_mode[1:0]"],
             "outputs": ["ras_ipdp_data_vld", "ras_ipdp_pc[38:0]", "ras_l0_btb_pc[38:0]", "ras_l0_btb_push_pc[38:0]"]},
            {"name": "vector", "type": "ct_ifu_vector",
             "description": "Vector interrupt handler: reset vector, interrupt vector table base (11 inputs, 10 outputs)",
             "inputs": ["cp0_ifu_icg_en", "cp0_ifu_rst_inv_done", "cp0_ifu_rvbr[39:0]", "cp0_ifu_vbr[39:0]"],
             "outputs": ["ifu_cp0_rst_inv_req", "ifu_xx_sync_reset", "vector_debug_cur_st[9:0]", "vector_debug_reset_on"]},
            {"name": "debug", "type": "ct_ifu_debug",
             "description": "IFU debug: hardware debug interface, breakpoint, single-step (49 inputs, 2 outputs)",
             "inputs": ["cpurst_b", "forever_cpuclk", "had_rtu_xx_jdbreq", "ibctrl_debug_buf_stall"],
             "outputs": ["ifu_had_debug_info[82:0]", "ifu_had_reset_on"]},
        ],
    },
    "idu": {
        "submodules": [
            {"name": "id_ctrl", "type": "ct_idu_id_ctrl",
             "description": "Instruction decode control: decode stage pipeline control and stall (33 inputs, 27 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_yy_clk_en", "cpurst_b", "ctrl_ir_stage_stall"],
             "outputs": ["ctrl_dp_id_debug_id_pipedown3", "ctrl_dp_id_inst0_vld", "ctrl_dp_id_inst1_vld", "ctrl_dp_id_inst2_vld"]},
            {"name": "id_dp", "type": "ct_idu_id_dp",
             "description": "Instruction decode datapath: opcode/funct/imm extraction per instruction (32 inputs, 31 outputs)",
             "inputs": ["cp0_idu_cskyee", "cp0_idu_frm[2:0]", "cp0_idu_fs[1:0]", "cp0_idu_icg_en"],
             "outputs": ["dp_ctrl_id_inst0_fence", "dp_ctrl_id_inst0_normal", "dp_ctrl_id_inst0_split_long", "dp_ctrl_id_inst0_split_short"]},
            {"name": "id_fence", "type": "ct_idu_id_fence",
             "description": "Fence instruction handling: fence.i/fence/sfence.vma ordering control (23 inputs, 11 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_yy_clk_en", "cpurst_b", "ctrl_fence_id_inst_vld"],
             "outputs": ["fence_ctrl_id_stall", "fence_ctrl_inst0_vld", "fence_ctrl_inst1_vld", "fence_ctrl_inst2_vld"]},
            {"name": "ir_ctrl", "type": "ct_idu_ir_ctrl",
             "description": "Instruction rename control: rename stage pipeline control, IQ allocation (84 inputs, 100 outputs)",
             "inputs": ["aiq0_ctrl_entry_cnt_updt_val[3:0]", "aiq0_ctrl_entry_cnt_updt_vld", "aiq1_ctrl_entry_cnt_updt_val[3:0]", "aiq1_ctrl_entry_cnt_updt_vld"],
             "outputs": ["ctrl_dp_ir_inst0_vld", "ctrl_fence_ir_pipe_empty", "ctrl_ir_pipedown", "ctrl_ir_pipedown_gateclk"]},
            {"name": "ir_dp", "type": "ct_idu_ir_dp",
             "description": "Instruction rename datapath: decoded instruction payload to rename (103 inputs, 173 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_yy_clk_en", "cpurst_b", "ctrl_dp_ir_inst0_vld"],
             "outputs": ["dp_ctrl_ir_inst0_bar", "dp_ctrl_ir_inst0_ctrl_info[12:0]", "dp_ctrl_ir_inst0_dst_vld", "dp_ctrl_ir_inst0_dst_x0"]},
            {"name": "ir_rt", "type": "ct_idu_ir_rt",
             "description": "Integer register rename table: architectual→physical register mapping (77 inputs, 22 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_yy_clk_en", "cpurst_b", "ctrl_ir_stall"],
             "outputs": ["rt_dp_inst01_src_match[2:0]", "rt_dp_inst02_src_match[2:0]", "rt_dp_inst03_src_match[2:0]", "rt_dp_inst0_rel_preg[6:0]"]},
            {"name": "ir_frt", "type": "ct_idu_ir_frt",
             "description": "Floating-point register rename table: FP arch→phys mapping (98 inputs, 26 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_yy_clk_en", "cpurst_b", "ctrl_ir_stall"],
             "outputs": ["frt_dp_inst01_srcf2_match", "frt_dp_inst02_srcf2_match", "frt_dp_inst03_srcf2_match", "frt_dp_inst0_rel_ereg[4:0]"]},
            {"name": "ir_vrt", "type": "ct_idu_ir_vrt",
             "description": "Vector register rename table: vector arch→phys mapping (41 inputs, 26 outputs)",
             "inputs": ["dp_vrt_inst0_dst_vreg[5:0]", "dp_vrt_inst0_dstv_reg[5:0]", "dp_vrt_inst0_dstv_vld", "dp_vrt_inst0_srcv0_reg[5:0]"],
             "outputs": ["vrt_dp_inst01_srcv2_match", "vrt_dp_inst02_srcv2_match", "vrt_dp_inst03_srcv2_match", "vrt_dp_inst0_rel_vreg[6:0]"]},
            {"name": "is_ctrl", "type": "ct_idu_is_ctrl",
             "description": "Issue select control: wakeup-select logic, oldest-ready arbitration (127 inputs, 137 outputs)",
             "inputs": ["aiq0_ctrl_1_left_updt", "aiq0_ctrl_empty", "aiq0_ctrl_full", "aiq0_ctrl_full_updt"],
             "outputs": ["ctrl_aiq0_create0_dp_en", "ctrl_aiq0_create0_en", "ctrl_aiq0_create0_gateclk_en", "ctrl_aiq0_create1_dp_en"]},
            {"name": "is_dp", "type": "ct_idu_is_dp",
             "description": "Issue select datapath: issue entry read, bypass path muxing (175 inputs, 158 outputs)",
             "inputs": ["aiq0_aiq_create0_entry[7:0]", "aiq0_aiq_create1_entry[7:0]", "aiq1_aiq_create0_entry[7:0]", "aiq1_aiq_create1_entry[7:0]"],
             "outputs": ["dp_aiq0_bypass_data[226:0]", "dp_aiq0_create0_data[226:0]", "dp_aiq0_create1_data[226:0]", "dp_aiq0_create_div"]},
            {"name": "is_aiq0", "type": "ct_idu_is_aiq0",
             "description": "ALU issue queue 0: 32-entry wakeup-select for pipe0 (ALU0) (102 inputs, 14 outputs)",
             "inputs": ["aiq1_aiq_create0_entry[7:0]", "aiq1_aiq_create1_entry[7:0]", "biq_aiq_create0_entry[11:0]", "biq_aiq_create1_entry[11:0]"],
             "outputs": ["aiq0_aiq_create0_entry[7:0]", "aiq0_aiq_create1_entry[7:0]", "aiq0_ctrl_1_left_updt", "aiq0_ctrl_empty"]},
            {"name": "is_aiq1", "type": "ct_idu_is_aiq1",
             "description": "ALU issue queue 1: 32-entry wakeup-select for pipe1 (ALU1) (103 inputs, 14 outputs)",
             "inputs": ["aiq0_aiq_create0_entry[7:0]", "aiq0_aiq_create1_entry[7:0]", "biq_aiq_create0_entry[11:0]", "biq_aiq_create1_entry[11:0]"],
             "outputs": ["aiq1_aiq_create0_entry[7:0]", "aiq1_aiq_create1_entry[7:0]", "aiq1_ctrl_1_left_updt", "aiq1_ctrl_empty"]},
            {"name": "is_biq", "type": "ct_idu_is_biq",
             "description": "Branch issue queue: issue queue for branch/jump instructions (49 inputs, 12 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_idu_iq_bypass_disable", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["biq_aiq_create0_entry[11:0]", "biq_aiq_create1_entry[11:0]", "biq_ctrl_1_left_updt", "biq_ctrl_empty"]},
            {"name": "is_lsiq", "type": "ct_idu_is_lsiq",
             "description": "Load/store issue queue: issue queue for memory instructions (101 inputs, 18 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_idu_iq_bypass_disable", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["lsiq_aiq_create0_entry[11:0]", "lsiq_aiq_create1_entry[11:0]", "lsiq_ctrl_1_left_updt", "lsiq_ctrl_empty"]},
            {"name": "is_sdiq", "type": "ct_idu_is_sdiq",
             "description": "Shared issue queue: shared queue for multi-cycle operations (77 inputs, 17 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_yy_clk_en", "cpurst_b", "ctrl_sdiq_create0_dp_en"],
             "outputs": ["idu_rtu_pst_freg_dealloc_mask[63:0]", "idu_rtu_pst_preg_dealloc_mask[95:0]", "idu_rtu_pst_vreg_dealloc_mask[63:0]", "sdiq_aiq_create0_entry[11:0]"]},
            {"name": "is_viq0", "type": "ct_idu_is_viq0",
             "description": "Vector issue queue 0: issue queue for vector instructions (pipe6) (77 inputs, 14 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_idu_iq_bypass_disable", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["viq0_ctrl_1_left_updt", "viq0_ctrl_empty", "viq0_ctrl_entry_cnt_updt_val[3:0]", "viq0_ctrl_entry_cnt_updt_vld"]},
            {"name": "is_viq1", "type": "ct_idu_is_viq1",
             "description": "Vector issue queue 1: issue queue for vector instructions (pipe7) (75 inputs, 14 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_idu_iq_bypass_disable", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["viq1_ctrl_1_left_updt", "viq1_ctrl_empty", "viq1_ctrl_entry_cnt_updt_val[3:0]", "viq1_ctrl_entry_cnt_updt_vld"]},
            {"name": "rf_ctrl", "type": "ct_idu_rf_ctrl",
             "description": "Register file control: register read/write port arbitration, forwarding control (73 inputs, 111 outputs)",
             "inputs": ["aiq0_xx_gateclk_issue_en", "aiq0_xx_issue_en", "aiq1_xx_gateclk_issue_en", "aiq1_xx_issue_en"],
             "outputs": ["ctrl_aiq0_rf_lch_fail_vld", "ctrl_aiq0_rf_pipe0_alu_reg_fwd_vld[23:0]", "ctrl_aiq0_rf_pipe1_alu_reg_fwd_vld[23:0]", "ctrl_aiq0_rf_pop_dlb_vld"]},
            {"name": "rf_dp", "type": "ct_idu_rf_dp",
             "description": "Register file datapath: operand read muxing, bypass network (152 inputs, 307 outputs)",
             "inputs": ["aiq0_dp_issue_entry[7:0]", "aiq0_dp_issue_read_data[226:0]", "aiq0_xx_gateclk_issue_en", "aiq0_xx_issue_en"],
             "outputs": ["dp_aiq0_rf_lch_entry[7:0]", "dp_aiq0_rf_rdy_clr[2:0]", "dp_aiq1_rf_lch_entry[7:0]", "dp_aiq1_rf_rdy_clr[2:0]"]},
            {"name": "rf_fwd", "type": "ct_idu_rf_fwd",
             "description": "Register file forwarding: operand forwarding between execution pipes (86 inputs, 63 outputs)",
             "inputs": ["cp0_idu_src2_fwd_disable", "cp0_idu_srcv2_fwd_disable", "dp_fwd_rf_pipe0_src0_preg[6:0]", "dp_fwd_rf_pipe0_src1_preg[6:0]"],
             "outputs": ["fwd_dp_rf_pipe0_src0_data[63:0]", "fwd_dp_rf_pipe0_src0_no_fwd", "fwd_dp_rf_pipe0_src1_data[63:0]", "fwd_dp_rf_pipe0_src1_no_fwd"]},
            {"name": "rf_prf_pregfile", "type": "ct_idu_rf_prf_pregfile",
             "description": "Physical register file (int): 128×64-bit integer physical registers (25 inputs, 13 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_yy_clk_en", "dp_prf_rf_pipe0_src0_preg[6:0]", "dp_prf_rf_pipe0_src1_preg[6:0]"],
             "outputs": ["idu_had_wb_data[63:0]", "idu_had_wb_vld", "prf_dp_rf_pipe0_src0_data[63:0]", "prf_dp_rf_pipe0_src1_data[63:0]"]},
            {"name": "rf_prf_eregfile", "type": "ct_idu_rf_prf_eregfile",
             "description": "Physical register file (exception): exception register state storage (13 inputs, 2 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["idu_cp0_fesr_acc_updt_val[6:0]", "idu_cp0_fesr_acc_updt_vld"]},
            {"name": "rf_prf_fregfile", "type": "ct_idu_rf_prf_fregfile",
             "description": "Physical register file (FP): 128×64-bit FP physical registers (20 inputs, 7 outputs)",
             "inputs": ["cp0_idu_icg_en", "cp0_yy_clk_en", "dp_prf_rf_pipe5_srcv0_vreg[5:0]", "dp_prf_rf_pipe6_srcv0_vreg[5:0]"],
             "outputs": ["prf_dp_rf_pipe5_srcv0_vreg_data[63:0]", "prf_dp_rf_pipe6_srcv0_vreg_data[63:0]", "prf_dp_rf_pipe6_srcv1_vreg_data[63:0]", "prf_dp_rf_pipe6_srcv2_vreg_data[63:0]"]},
            {"name": "rf_prf_vregfile", "type": "ct_idu_rf_prf_vregfile",
             "description": "ct_idu_rf_prf_vregfile (18 inputs, 9 outputs)",
             "inputs": ["dp_prf_rf_pipe5_srcv0_vreg[5:0]", "dp_prf_rf_pipe6_srcv0_vreg[5:0]", "dp_prf_rf_pipe6_srcv1_vreg[5:0]", "dp_prf_rf_pipe6_srcv2_vreg[5:0]"],
             "outputs": ["prf_dp_rf_pipe5_srcv0_vreg_data[63:0]", "prf_dp_rf_pipe6_srcv0_vreg_data[63:0]", "prf_dp_rf_pipe6_srcv1_vreg_data[63:0]", "prf_dp_rf_pipe6_srcv2_vreg_data[63:0]"]},
            {"name": "rf_prf_vregfile", "type": "ct_idu_rf_prf_vregfile",
             "description": "ct_idu_rf_prf_vregfile (18 inputs, 9 outputs)",
             "inputs": ["dp_prf_rf_pipe5_srcv0_vreg[5:0]", "dp_prf_rf_pipe6_srcv0_vreg[5:0]", "dp_prf_rf_pipe6_srcv1_vreg[5:0]", "dp_prf_rf_pipe6_srcv2_vreg[5:0]"],
             "outputs": ["prf_dp_rf_pipe5_srcv0_vreg_data[63:0]", "prf_dp_rf_pipe6_srcv0_vreg_data[63:0]", "prf_dp_rf_pipe6_srcv1_vreg_data[63:0]", "prf_dp_rf_pipe6_srcv2_vreg_data[63:0]"]},
        ],
    },
    "iu": {
        "submodules": [
            {"name": "alu", "type": "ct_iu_alu",
             "description": "Integer ALU: ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU, 2-stage pipelined (24 inputs, 13 outputs)",
             "inputs": ["cp0_iu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["alu_rbus_ex1_pipex_data[63:0]", "alu_rbus_ex1_pipex_data_vld", "alu_rbus_ex1_pipex_fwd_data[63:0]", "alu_rbus_ex1_pipex_fwd_vld"]},
            {"name": "alu", "type": "ct_iu_alu",
             "description": "Integer ALU: ADD/SUB/XOR/OR/AND/SLL/SRL/SRA/SLT/SLTU, 2-stage pipelined (24 inputs, 13 outputs)",
             "inputs": ["cp0_iu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["alu_rbus_ex1_pipex_data[63:0]", "alu_rbus_ex1_pipex_data_vld", "alu_rbus_ex1_pipex_fwd_data[63:0]", "alu_rbus_ex1_pipex_fwd_vld"]},
            {"name": "bju", "type": "ct_iu_bju",
             "description": "Branch execution unit: branch condition resolution, target calculation (50 inputs, 29 outputs)",
             "inputs": ["cp0_iu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["bju_cbus_ex2_pipe2_abnormal", "bju_cbus_ex2_pipe2_bht_mispred", "bju_cbus_ex2_pipe2_iid[6:0]", "bju_cbus_ex2_pipe2_jmp_mispred"]},
            {"name": "mult", "type": "ct_iu_mult",
             "description": "Multiplier: 65×65-bit 3-stage pipelined integer multiplier (15 inputs, 16 outputs)",
             "inputs": ["cp0_iu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["iu_idu_ex1_pipe1_mult_stall", "iu_idu_ex2_pipe1_mult_inst_vld_dup0", "iu_idu_ex2_pipe1_mult_inst_vld_dup1", "iu_idu_ex2_pipe1_mult_inst_vld_dup2"]},
            {"name": "div", "type": "ct_iu_div",
             "description": "Divider: radix-16 SRT integer divider, variable latency (17 inputs, 13 outputs)",
             "inputs": ["cp0_iu_div_entry_disable", "cp0_iu_div_entry_disable_clr", "cp0_iu_icg_en", "cp0_yy_clk_en"],
             "outputs": ["div_rbus_data[63:0]", "div_rbus_pipe0_data_vld", "div_rbus_preg[6:0]", "div_top_div_no_idle"]},
            {"name": "special", "type": "ct_iu_special",
             "description": "Special unit: CSR access, fence, ecall/ebreak, system instructions (26 inputs, 17 outputs)",
             "inputs": ["bju_special_pc[39:0]", "cp0_iu_icg_en", "cp0_iu_vill", "cp0_iu_vl[7:0]"],
             "outputs": ["special_cbus_ex1_abnormal", "special_cbus_ex1_bkpt", "special_cbus_ex1_expt_vec[4:0]", "special_cbus_ex1_expt_vld"]},
            {"name": "cbus", "type": "ct_iu_cbus",
             "description": "Completion bus: collect execution results, broadcast to ROB/reservation stations (42 inputs, 22 outputs)",
             "inputs": ["bju_cbus_ex2_pipe2_abnormal", "bju_cbus_ex2_pipe2_bht_mispred", "bju_cbus_ex2_pipe2_iid[6:0]", "bju_cbus_ex2_pipe2_jmp_mispred"],
             "outputs": ["iu_rtu_pipe0_abnormal", "iu_rtu_pipe0_bkpt", "iu_rtu_pipe0_cmplt", "iu_rtu_pipe0_efpc[38:0]"]},
            {"name": "rbus", "type": "ct_iu_rbus",
             "description": "Result bus: broadcast execution results to register file and forwarding network (37 inputs, 38 outputs)",
             "inputs": ["alu_rbus_ex1_pipe0_data[63:0]", "alu_rbus_ex1_pipe0_data_vld", "alu_rbus_ex1_pipe0_fwd_data[63:0]", "alu_rbus_ex1_pipe0_fwd_vld"],
             "outputs": ["iu_idu_ex1_pipe0_fwd_preg[6:0]", "iu_idu_ex1_pipe0_fwd_preg_data[63:0]", "iu_idu_ex1_pipe0_fwd_preg_vld", "iu_idu_ex1_pipe1_fwd_preg[6:0]"]},
        ],
    },
    "lsu": {
        "submodules": [
            {"name": "ld_ag", "type": "ct_lsu_ld_ag",
             "description": "Load address generator: load virtual address calculation and TLB lookup (59 inputs, 82 outputs)",
             "inputs": ["cp0_lsu_cb_aclr_dis", "cp0_lsu_da_fwd_dis", "cp0_lsu_dcache_en", "cp0_lsu_icg_en"],
             "outputs": ["ag_dcache_arb_ld_data_gateclk_en[7:0]", "ag_dcache_arb_ld_data_high_idx[10:0]", "ag_dcache_arb_ld_data_low_idx[10:0]", "ag_dcache_arb_ld_data_req[7:0]"]},
            {"name": "st_ag", "type": "ct_lsu_st_ag",
             "description": "Store address generator: store virtual address calculation and TLB lookup (75 inputs, 66 outputs)",
             "inputs": ["cp0_lsu_dcache_en", "cp0_lsu_icg_en", "cp0_lsu_mm", "cp0_lsu_tvm"],
             "outputs": ["ag_dcache_arb_st_dirty_gateclk_en", "ag_dcache_arb_st_dirty_idx[8:0]", "ag_dcache_arb_st_dirty_req", "ag_dcache_arb_st_tag_gateclk_en"]},
            {"name": "sd_ex1", "type": "ct_lsu_sd_ex1",
             "description": "Store data EX1: store data alignment and formatting (18 inputs, 8 outputs)",
             "inputs": ["cp0_lsu_icg_en", "cp0_yy_clk_en", "cpurst_b", "ctrl_st_clk"],
             "outputs": ["lsu_idu_ex1_sdiq_entry[11:0]", "lsu_idu_ex1_sdiq_frz_clr", "lsu_idu_ex1_sdiq_pop_vld", "sd_ex1_data[63:0]"]},
            {"name": "mcic", "type": "ct_lsu_mcic",
             "description": "Memory coherence interface controller: L2/memory request ordering (23 inputs, 13 outputs)",
             "inputs": ["biu_lsu_r_data[127:0]", "biu_lsu_r_id[4:0]", "biu_lsu_r_resp[3:0]", "biu_lsu_r_vld"],
             "outputs": ["lsu_had_mcic_data_req", "lsu_had_mcic_frz", "lsu_mmu_bus_error", "lsu_mmu_data[63:0]"]},
            {"name": "dcache_arb", "type": "ct_lsu_dcache_arb",
             "description": "D-cache arbiter: arbitrate load/store/snoop/prefetch access to dcache (141 inputs, 65 outputs)",
             "inputs": ["ag_dcache_arb_ld_data_gateclk_en[7:0]", "ag_dcache_arb_ld_data_high_idx[10:0]", "ag_dcache_arb_ld_data_low_idx[10:0]", "ag_dcache_arb_ld_data_req[7:0]"],
             "outputs": ["dcache_arb_ag_ld_sel", "dcache_arb_ag_st_sel", "dcache_arb_icc_ld_grnt", "dcache_arb_ld_ag_addr[39:0]"]},
            {"name": "dcache_top", "type": "ct_lsu_dcache_top",
             "description": "D-cache top-level: SRAM array aggregation and data output muxing (29 inputs, 11 outputs)",
             "inputs": ["cp0_lsu_icg_en", "forever_cpuclk", "lsu_dcache_ld_data_gateclk_en[7:0]", "lsu_dcache_ld_data_gwen_b[7:0]"],
             "outputs": ["dcache_lsu_ld_data_bank0_dout[31:0]", "dcache_lsu_ld_data_bank1_dout[31:0]", "dcache_lsu_ld_data_bank2_dout[31:0]", "dcache_lsu_ld_data_bank3_dout[31:0]"]},
            {"name": "ld_dc", "type": "ct_lsu_ld_dc",
             "description": "Load data control: load miss handling, fill data steering (104 inputs, 114 outputs)",
             "inputs": ["cb_ld_dc_addr_hit", "cp0_lsu_da_fwd_dis", "cp0_lsu_dcache_en", "cp0_lsu_icg_en"],
             "outputs": ["ld_dc_addr0[39:0]", "ld_dc_addr1[39:0]", "ld_dc_addr1_11to4[7:0]", "ld_dc_ahead_predict"]},
            {"name": "st_dc", "type": "ct_lsu_st_dc",
             "description": "Store data control: store buffer management, write merging (81 inputs, 77 outputs)",
             "inputs": ["cp0_lsu_dcache_en", "cp0_lsu_icg_en", "cp0_lsu_l2_st_pref_en", "cp0_yy_clk_en"],
             "outputs": ["lsu_idu_dc_sdiq_entry[11:0]", "lsu_idu_dc_staddr1_vld", "lsu_idu_dc_staddr_unalign", "lsu_idu_dc_staddr_vld"]},
            {"name": "lq", "type": "ct_lsu_lq",
             "description": "Load queue: 16-entry in-order load tracking for precise exceptions (32 inputs, 6 outputs)",
             "inputs": ["cp0_lsu_corr_dis", "cp0_lsu_icg_en", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["lq_ld_dc_full", "lq_ld_dc_inst_hit", "lq_ld_dc_less2", "lq_ld_dc_spec_fail"]},
            {"name": "sq", "type": "ct_lsu_sq",
             "description": "Store queue: 16-entry in-order store tracking with forwarding support (97 inputs, 69 outputs)",
             "inputs": ["cp0_lsu_icg_en", "cp0_yy_clk_en", "cp0_yy_priv_mode[1:0]", "cpurst_b"],
             "outputs": ["lsu_had_sq_not_empty", "lsu_had_st_addr[39:0]", "lsu_had_st_data[63:0]", "lsu_had_st_iid[6:0]"]},
            {"name": "ld_da", "type": "ct_lsu_ld_da",
             "description": "Load data array: load data SRAM access, byte masking, alignment (120 inputs, 129 outputs)",
             "inputs": ["cb_ld_da_data[127:0]", "cb_ld_da_data_vld", "cp0_lsu_dcache_en", "cp0_lsu_icg_en"],
             "outputs": ["ld_da_addr[39:0]", "ld_da_bkpta_data", "ld_da_bkptb_data", "ld_da_borrow_vld"]},
            {"name": "st_da", "type": "ct_lsu_st_da",
             "description": "Store data array: store data SRAM access, byte write enables (84 inputs, 93 outputs)",
             "inputs": ["amr_wa_cancel", "cp0_lsu_dcache_en", "cp0_lsu_icg_en", "cp0_lsu_l2_st_pref_en"],
             "outputs": ["lsu_hpcp_st_cache_access", "lsu_hpcp_st_cache_miss", "lsu_hpcp_st_unalign_inst", "lsu_rtu_da_pipe4_split_spec_fail_iid[6:0]"]},
            {"name": "rb", "type": "ct_lsu_rb",
             "description": "Reorder buffer (LSU): bus response reordering for out-of-order bus responses (101 inputs, 75 outputs)",
             "inputs": ["biu_lsu_b_id[4:0]", "biu_lsu_b_vld", "biu_lsu_r_data[127:0]", "biu_lsu_r_id[4:0]"],
             "outputs": ["lsu_had_rb_entry_fence[7:0]", "lsu_had_rb_entry_state_0[3:0]", "lsu_had_rb_entry_state_1[3:0]", "lsu_had_rb_entry_state_2[3:0]"]},
            {"name": "wmb", "type": "ct_lsu_wmb",
             "description": "Write merge buffer: merge multiple write requests to same cache line (117 inputs, 121 outputs)",
             "inputs": ["amr_l2_mem_set", "biu_lsu_b_id[4:0]", "biu_lsu_b_resp[1:0]", "biu_lsu_b_vld"],
             "outputs": ["lsu_had_wmb_ar_pending", "lsu_had_wmb_aw_pending", "lsu_had_wmb_create_ptr[7:0]", "lsu_had_wmb_data_ptr[7:0]"]},
            {"name": "wmb_ce", "type": "ct_lsu_wmb_ce",
             "description": "Write merge buffer control: write merge arbitration and coherence (39 inputs, 41 outputs)",
             "inputs": ["cp0_lsu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["wmb_ce_addr[39:0]", "wmb_ce_atomic", "wmb_ce_bytes_vld[15:0]", "wmb_ce_bytes_vld_full"]},
            {"name": "ld_wb", "type": "ct_lsu_ld_wb",
             "description": "Load writeback: load result writeback to register file (56 inputs, 63 outputs)",
             "inputs": ["cp0_lsu_icg_en", "cp0_yy_clk_en", "cpurst_b", "ctrl_ld_clk"],
             "outputs": ["ld_wb_data_vld", "ld_wb_inst_vld", "ld_wb_rb_cmplt_grnt", "ld_wb_rb_data_grnt"]},
            {"name": "st_wb", "type": "ct_lsu_st_wb",
             "description": "Store writeback: store completion writeback and notification (25 inputs, 15 outputs)",
             "inputs": ["cp0_lsu_icg_en", "cp0_yy_clk_en", "cpurst_b", "ctrl_st_clk"],
             "outputs": ["lsu_rtu_wb_pipe4_abnormal", "lsu_rtu_wb_pipe4_bkpta_data", "lsu_rtu_wb_pipe4_bkptb_data", "lsu_rtu_wb_pipe4_cmplt"]},
            {"name": "lfb", "type": "ct_lsu_lfb",
             "description": "Line fill buffer: cache line fill data buffering from L2/memory (53 inputs, 59 outputs)",
             "inputs": ["biu_lsu_r_data[127:0]", "biu_lsu_r_id[4:0]", "biu_lsu_r_last", "biu_lsu_r_resp[3:0]"],
             "outputs": ["ld_hit_prefetch", "lfb_addr_full", "lfb_addr_less2", "lfb_dcache_arb_ld_data_gateclk_en[7:0]"]},
            {"name": "vb", "type": "ct_lsu_vb",
             "description": "Victim buffer: evicted cache line storage for writeback (66 inputs, 88 outputs)",
             "inputs": ["biu_lsu_b_id[4:0]", "biu_lsu_b_vld", "bus_arb_vb_aw_grnt", "bus_arb_vb_w_grnt"],
             "outputs": ["lsu_had_vb_addr_entry_vld[1:0]", "lsu_had_vb_data_entry_vld[2:0]", "lsu_had_vb_rcl_sm_state[3:0]", "snq_data_bypass_hit[2:0]"]},
            {"name": "vb_sdb_data", "type": "ct_lsu_vb_sdb_data",
             "description": "Victim buffer store data: victim write data storage (26 inputs, 22 outputs)",
             "inputs": ["cp0_lsu_icg_en", "cpurst_b", "forever_cpuclk", "ld_da_data256[255:0]"],
             "outputs": ["sdb_data_vld[2:0]", "sdb_entry_avail[2:0]", "sdb_entry_data_0[127:0]", "sdb_entry_data_1[127:0]"]},
            {"name": "snoop_req_arbiter", "type": "ct_lsu_snoop_req_arbiter",
             "description": "Snoop request arbiter: arbitrate incoming snoop requests from bus (21 inputs, 16 outputs)",
             "inputs": ["biu_lsu_ac_addr[39:0]", "biu_lsu_ac_prot[2:0]", "biu_lsu_ac_req", "biu_lsu_ac_snoop[3:0]"],
             "outputs": ["arb_ctcq_ctc_2nd_trans", "arb_ctcq_ctc_asid_va[23:0]", "arb_ctcq_ctc_type[5:0]", "arb_ctcq_ctc_va_pa[35:0]"]},
            {"name": "snoop_resp", "type": "ct_lsu_snoop_resp",
             "description": "Snoop response: generate snoop response for cache coherence protocol (9 inputs, 9 outputs)",
             "inputs": ["biu_lsu_cd_ready", "biu_lsu_cr_ready", "ctcq_biu_cr_resp[4:0]", "ctcq_biu_cr_valid"],
             "outputs": ["biu_ctcq_cr_ready", "biu_lsu_cr_resp_acept", "biu_sdb_cd_ready", "biu_snq_cr_ready"]},
            {"name": "snoop_ctcq", "type": "ct_lsu_snoop_ctcq",
             "description": "Coherence transaction queue: track in-flight coherence transactions (14 inputs, 19 outputs)",
             "inputs": ["arb_ctcq_ctc_2nd_trans", "arb_ctcq_ctc_asid_va[23:0]", "arb_ctcq_ctc_type[5:0]", "arb_ctcq_ctc_va_pa[35:0]"],
             "outputs": ["ctcq_biu_2_cmplt", "ctcq_biu_cr_resp[4:0]", "ctcq_biu_cr_valid", "cur_ctcq_entry_empty"]},
            {"name": "snoop_snq", "type": "ct_lsu_snoop_snq",
             "description": "Snoop queue: queue of incoming snoop requests to process (45 inputs, 62 outputs)",
             "inputs": ["arb_snq_entry_oldest_index[5:0]", "arb_snq_snoop_addr[39:0]", "arb_snq_snoop_depd[9:0]", "arb_snq_snoop_prot[2:0]"],
             "outputs": ["cur_snq_entry_empty", "lsu_had_cdr_state[1:0]", "lsu_had_sdb_entry_vld[2:0]", "lsu_had_snoop_data_req"]},
            {"name": "lm", "type": "ct_lsu_lm",
             "description": "Load miss: handle load misses to L2/memory, page walk request (40 inputs, 17 outputs)",
             "inputs": ["biu_lsu_r_id[4:0]", "biu_lsu_r_resp[3:0]", "biu_lsu_r_vld", "cp0_lsu_icg_en"],
             "outputs": ["lm_addr_pa[27:0]", "lm_already_snoop", "lm_ld_da_hit_idx", "lm_lfb_depd_wakeup"]},
            {"name": "amr", "type": "ct_lsu_amr",
             "description": "Atomic memory operation: atomic RMW (AMOSWAP/AMOADD/...) execution (14 inputs, 3 outputs)",
             "inputs": ["cp0_lsu_amr", "cp0_lsu_amr2", "cp0_lsu_icg_en", "cp0_lsu_no_op_req"],
             "outputs": ["amr_l2_mem_set", "amr_wa_cancel", "lsu_had_amr_state[2:0]"]},
            {"name": "icc", "type": "ct_lsu_icc",
             "description": "Inter-core coherence: multi-core cache coherence protocol handling (29 inputs, 37 outputs)",
             "inputs": ["cp0_lsu_dcache_clr", "cp0_lsu_dcache_inv", "cp0_lsu_dcache_read_index[16:0]", "cp0_lsu_dcache_read_ld_tag"],
             "outputs": ["icc_dcache_arb_data_way", "icc_dcache_arb_ld_borrow_req", "icc_dcache_arb_ld_data_gateclk_en[7:0]", "icc_dcache_arb_ld_data_high_idx[10:0]"]},
            {"name": "ctrl", "type": "ct_lsu_ctrl",
             "description": "LSU control: overall LSU pipeline control, stall, flush generation (158 inputs, 44 outputs)",
             "inputs": ["cp0_lsu_dcache_pref_dist[1:0]", "cp0_lsu_icg_en", "cp0_lsu_l2_pref_dist[1:0]", "cp0_yy_clk_en"],
             "outputs": ["ctrl_ld_clk", "ctrl_st_clk", "lsu_had_debug_info[183:0]", "lsu_had_no_op"]},
            {"name": "bus_arb", "type": "ct_lsu_bus_arb",
             "description": "Bus arbiter: arbitrate BIU read/write/snoop channel access (99 inputs, 66 outputs)",
             "inputs": ["biu_lsu_ar_ready", "biu_lsu_aw_vb_grnt", "biu_lsu_aw_wmb_grnt", "biu_lsu_w_vb_grnt"],
             "outputs": ["bus_arb_pfu_ar_grnt", "bus_arb_pfu_ar_ready", "bus_arb_pfu_ar_sel", "bus_arb_rb_ar_grnt"]},
            {"name": "pfu", "type": "ct_lsu_pfu",
             "description": "Prefetch unit: hardware prefetcher with stride/stream detection (69 inputs, 28 outputs)",
             "inputs": ["amr_wa_cancel", "bus_arb_pfu_ar_grnt", "bus_arb_pfu_ar_ready", "cp0_lsu_dcache_en"],
             "outputs": ["lsu_mmu_va2[27:0]", "lsu_mmu_va2_vld", "pfu_biu_ar_addr[39:0]", "pfu_biu_ar_bar[1:0]"]},
            {"name": "cache_buffer", "type": "ct_lsu_cache_buffer",
             "description": "Cache buffer: temporary cache line data storage for fill/eviction (19 inputs, 3 outputs)",
             "inputs": ["cp0_lsu_cb_aclr_dis", "cp0_lsu_dcache_en", "cp0_lsu_icg_en", "cp0_lsu_no_op_req"],
             "outputs": ["cb_ld_da_data[127:0]", "cb_ld_da_data_vld", "cb_ld_dc_addr_hit"]},
            {"name": "spec_fail_predict", "type": "ct_lsu_spec_fail_predict",
             "description": "Speculative fail predict: load speculation failure prediction (17 inputs, 2 outputs)",
             "inputs": ["cp0_lsu_icg_en", "cpurst_b", "forever_cpuclk", "ld_da_sf_addr_tto4[35:0]"],
             "outputs": ["sf_spec_hit", "sf_spec_mark"]},
        ],
    },
    "rtu": {
        "submodules": [
            {"name": "pst_preg", "type": "ct_rtu_pst_preg",
             "description": "Physical register status (int): track 256 integer physical regs (free/busy/ready) (52 inputs, 13 outputs)",
             "inputs": ["cp0_rtu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["pst_retire_retired_reg_wb", "pst_top_retired_reg_wb[2:0]", "rtu_had_inst_not_wb", "rtu_idu_alloc_preg0[6:0]"]},
            {"name": "pst_ereg", "type": "ct_rtu_pst_ereg",
             "description": "Physical register status (exception): track exception register state (39 inputs, 11 outputs)",
             "inputs": ["cp0_rtu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["pst_retired_ereg_wb", "rtu_idu_alloc_ereg0[4:0]", "rtu_idu_alloc_ereg0_vld", "rtu_idu_alloc_ereg1[4:0]"]},
            {"name": "pst_vreg_dummy", "type": "ct_rtu_pst_vreg_dummy",
             "description": "Physical register status (vector dummy): vector register status placeholder (32 inputs, 10 outputs)",
             "inputs": ["idu_rtu_ir_xreg0_alloc_vld", "idu_rtu_ir_xreg1_alloc_vld", "idu_rtu_ir_xreg2_alloc_vld", "idu_rtu_ir_xreg3_alloc_vld"],
             "outputs": ["pst_retired_xreg_wb", "rtu_idu_alloc_xreg0[5:0]", "rtu_idu_alloc_xreg0_vld", "rtu_idu_alloc_xreg1[5:0]"]},
            {"name": "pst_vreg", "type": "ct_rtu_pst_vreg",
             "description": "ct_rtu_pst_vreg (49 inputs, 10 outputs)",
             "inputs": ["cp0_rtu_icg_en", "cp0_yy_clk_en", "cpurst_b", "forever_cpuclk"],
             "outputs": ["pst_retired_xreg_wb", "rtu_idu_alloc_xreg0[5:0]", "rtu_idu_alloc_xreg0_vld", "rtu_idu_alloc_xreg1[5:0]"]},
            {"name": "rob", "type": "ct_rtu_rob",
             "description": "Reorder buffer: 128-entry ROB, 4-wide allocate, in-order retire (116 inputs, 187 outputs)",
             "inputs": ["cp0_rtu_icg_en", "cp0_rtu_xx_int_b", "cp0_rtu_xx_vec[4:0]", "cp0_yy_clk_en"],
             "outputs": ["rob_pst_retire_inst0_gateclk_vld", "rob_pst_retire_inst0_iid[6:0]", "rob_pst_retire_inst0_iid_updt_val[6:0]", "rob_pst_retire_inst1_gateclk_vld"]},
            {"name": "retire", "type": "ct_rtu_retire",
             "description": "Retire unit: 4-wide instruction retirement, exception handling, commit (139 inputs, 171 outputs)",
             "inputs": ["cp0_rtu_icg_en", "cp0_rtu_srt_en", "cp0_yy_clk_en", "cpurst_b"],
             "outputs": ["retire_pst_async_flush", "retire_pst_wb_retire_inst0_ereg_vld", "retire_pst_wb_retire_inst0_preg_vld", "retire_pst_wb_retire_inst0_vreg_vld"]},
        ],
    },
}


def _create_hierarchical_base_module(pe: ProcessingElement,
                                     submod_def: dict) -> Module:
    """Create a hierarchical DSL Module with sub-module instantiations.

    Creates:
      - Parent module with ports
      - Sub-module skeleton modules (flat, ports only) for each sub-module
      - Internal wires for inter-sub-module connections
      - SubmoduleInst nodes connecting sub-modules

    Detailed logic for each sub-module is left for agents to implement.
    """
    module = Module(pe.name)
    module._type_name = pe.name
    module._has_submodules = True
    module._submodule_defs = submod_def.get("submodules", [])

    # Clock and reset
    module.clk = Input(1, "clk")
    module.rst_n = Input(1, "rst_n")

    # Parent-level ports
    for port in pe.inputs:
        setattr(module, port.name, Input(port.width, port.name))
    for port in pe.outputs:
        setattr(module, port.name, Output(port.width, port.name))

    parentinputs = {p.name for p in pe.inputs} | {"clk", "rst_n"}
    parentoutputs = {p.name for p in pe.outputs}

    # Build width map: parent ports + explicit port_widths from templates
    parent_port_widths = {p.name: p.width for p in pe.inputs}
    parent_port_widths.update({p.name: p.width for p in pe.outputs})
    parent_port_widths["clk"] = 1
    parent_port_widths["rst_n"] = 1

    # First pass: collect signal widths from all submodules
    # A signal's width = max(width from any source: parent port, template port_widths, default table, or pattern inference)
    signal_widths: Dict[str, int] = dict(parent_port_widths)
    for submod in submod_def.get("submodules", []):
        port_widths = submod.get("port_widths", {})
        for sig in submod.get("inputs", []):
            w = parent_port_widths.get(sig)
            if w is None:
                w = port_widths.get(sig)
            if w is None:
                w = _DEFAULT_SIGNAL_WIDTHS.get(sig)
            if w is None:
                w = _infer_signal_width(sig)
            signal_widths[sig] = max(signal_widths.get(sig, 1), w)
        for sig in submod.get("outputs", []):
            w = parent_port_widths.get(sig)
            if w is None:
                w = port_widths.get(sig)
            if w is None:
                w = _DEFAULT_SIGNAL_WIDTHS.get(sig)
            if w is None:
                w = _infer_signal_width(sig)
            signal_widths[sig] = max(signal_widths.get(sig, 1), w)

    # Collect all unique sub-module signal names that aren't parent ports
    internal_signals: set = set()
    for submod in submod_def.get("submodules", []):
        for sig in submod.get("inputs", []):
            if sig not in parentinputs and sig not in parentoutputs:
                internal_signals.add(sig)
        for sig in submod.get("outputs", []):
            if sig not in parentinputs and sig not in parentoutputs:
                internal_signals.add(sig)

    # Create internal wires for sub-module connections using inferred widths
    for sig in internal_signals:
        if not hasattr(module, sig):
            w = Wire(signal_widths.get(sig, _infer_signal_width(sig)), sig)
            setattr(module, sig, w)

    # Create sub-module skeletons and instantiate them
    for submod in submod_def.get("submodules", []):
        sub_name = submod["name"]
        sub_type = submod["type"]
        sub_inputs = submod.get("inputs", [])
        sub_outputs = submod.get("outputs", [])

        # Create sub-module with its own ports
        sub_mod = Module(sub_name)
        sub_mod._type_name = f"{pe.name}_{sub_type}"
        sub_mod._submodule_type = sub_type

        for sig in sub_inputs:
            width = signal_widths.get(sig, _infer_signal_width(sig))
            if not hasattr(sub_mod, sig):
                setattr(sub_mod, sig, Input(width, sig))
        for sig in sub_outputs:
            width = signal_widths.get(sig, _infer_signal_width(sig))
            if not hasattr(sub_mod, sig):
                setattr(sub_mod, sig, Output(width, sig))

        # Build port map: connect sub-module ports to parent/internal signals
        port_map = {}
        for sig in sub_inputs:
            if hasattr(module, sig):
                port_map[sig] = getattr(module, sig)
        for sig in sub_outputs:
            if hasattr(module, sig):
                port_map[sig] = getattr(module, sig)

        # Instantiate sub-module
        inst_name = f"u_{sub_name}"
        inst = SubmoduleInst(inst_name, sub_mod, {}, port_map)
        module._submodules.append((inst_name, sub_mod))
        module._top_level.append(inst)

    return module


def _declare_state_vars(module: Module, state_list: List[StateDesc]):
    """根据 StateDesc 声明状态变量。

    For regfile/memory/queue/fifo types with large depth, declare as
    Array instead of unrolling individual Regs to avoid skeleton bloat.
    Also handles multi-element reg types (e.g. per-warp state arrays).
    """
    for sd in state_list:
        if sd.rtl_type == "reg":
            width = sd.rtl_width or 32
            depth = sd.rtl_depth or 1
            if depth > 1:
                # Multi-element state (e.g. per-warp PC, per-lane accum)
                arr = Array(width, depth, sd.name)
                setattr(module, sd.name, arr)
            else:
                reg = Reg(width, sd.name)
                setattr(module, sd.name, reg)
        elif sd.rtl_type == "regfile":
            depth = sd.rtl_depth or 32
            width = sd.rtl_width or 32
            if depth <= 8:
                for i in range(depth):
                    reg = Reg(width, f"{sd.name}_{i}")
                    setattr(module, f"{sd.name}_{i}", reg)
            else:
                arr = Array(width, depth, sd.name)
                setattr(module, sd.name, arr)
        elif sd.rtl_type in ("memory", "queue", "fifo"):
            depth = sd.rtl_depth or 64
            width = sd.rtl_width or 32
            if depth <= 8:
                for i in range(depth):
                    reg = Reg(width, f"{sd.name}_{i}")
                    setattr(module, f"{sd.name}_{i}", reg)
            else:
                arr = Array(width, depth, sd.name)
                setattr(module, sd.name, arr)
        else:
            # Default: reg
            width = sd.rtl_width or 32
            reg = Reg(width, sd.name)
            setattr(module, sd.name, reg)


# =====================================================================
# Rule-Based Skeleton Logic Filler (Audit Fix 0522 — Section 2.3)
# =====================================================================
# Bridge the gap between empty skeleton shells and actual RTL logic.
# Generates comb/seq logic blocks based on PE type, using the ports
# and state vars already declared by _create_base_module and _declare_state_vars.


_TEMPLATE_STEPS: Dict[str, list] = {
    "ifu": [
        "1. 实现 PC 寄存器（seq block with reset）",
        "2. 实现 PC 递增逻辑（pc_next = pc + 4 * issue_width）",
        "3. 实现分支预测结构（BTB/BHT/RAS 查找）",
        "4. 整合预测结果到 PC 选择器",
        "5. 实现取指数据打包（指令 bundle 输出）",
        "6. 实现停顿/冲刷处理",
        "7. 验证：对比 behavior model 的 PC 序列和指令流",
    ],
    "idu": [
        "1. 实现指令解码逻辑（opcode → func）",
        "2. 实现寄存器重命名表（arch → preg）",
        "3. 实现分发队列（dispatch queue）",
        "4. 实现到各 pipe 的信号分发",
        "5. 实现 stall 处理（ROB full → stall IFU）",
        "6. 验证：对比 behavior model 的分发序列",
    ],
    "alu": [
        "1. 实现多 pipe 分发逻辑（opcode → pipe）",
        "2. 实现各 pipe 的算子（ALU/Mult/BJU）",
        "3. 实现旁路网络（bypass/forwarding）",
        "4. 实现 completion 信号到 RTU",
        "5. 实现异常/中断处理",
        "6. 验证：对比 behavior model 的运算结果",
    ],
    "lsu": [
        "1. 实现地址计算（base + offset）",
        "2. 实现 Load Queue / Store Queue",
        "3. 实现 D-Cache 接口",
        "4. 实现数据前递（load → ALU bypass）",
        "5. 实现内存序约束（fence/acquire/release）",
        "6. 验证：对比 behavior model 的访存序列",
    ],
    "rtu": [
        "1. 实现 ROB 队列（create → complete → retire）",
        "2. 实现 commit/retire 逻辑",
        "3. 实现异常/flush 生成",
        "4. 实现物理寄存器状态管理",
        "5. 验证：对比 behavior model 的 retire 序列",
    ],
    "regfile": [
        "1. 实现多读多写寄存器文件",
        "2. 实现读写端口仲裁",
        "3. 实现 bypass 逻辑（同时读写同一寄存器）",
        "4. 验证：对比 behavior model 的寄存器状态",
    ],
    "cache": [
        "1. 实现 tag/data 阵列",
        "2. 实现 LRU 替换逻辑",
        "3. 实现 miss/refill 状态机",
        "4. 实现写策略（write-through/write-back）",
        "5. 验证：对比行为模型的 hit/miss 模式",
    ],
    "cta_scheduler": [
        "1. 实现 inflight_wg_buffer：host 请求接收 + 缓冲",
        "2. 实现 allocator_neo：VGPR/SGPR/LDS 资源分配",
        "3. 实现 top_resource_table：全局资源跟踪",
        "4. 实现 dis_controller：dispatch FSM",
        "5. 验证：对比 behavior model 的资源分配",
    ],
    "warp_scheduler": [
        "1. 实现 warp_active 跟踪寄存器",
        "2. 实现 pc_control 实例的 generate 循环",
        "3. 实现 fixed priority arbiter",
        "4. 实现 barrier 同步状态机",
        "5. 验证：对比 behavior model 的 warp 调度",
    ],
    "pc_control": [
        "1. 实现 PC 选择器（pc_src: normal/jump/stall/halt）",
        "2. 实现 PC 递增逻辑",
        "3. 实现 stall/jump/halt 状态切换",
        "4. 验证：对比 behavior model 的 PC 序列",
    ],
    "pipe": [
        "1. 实现 Fetch/Decode/IBuffer/Issue/Execute/Writeback 各级",
        "2. 验证：对比 behavior model 的流水线执行序列",
    ],
    "arbiter": [
        "1. 实现请求输入和 grant 输出",
        "2. 实现仲裁算法（round-robin / fixed-priority）",
        "3. 验证：对比 behavior model 的仲裁序列",
    ],
    "shared_mem": [
        "1. 实现多 bank SRAM 阵列",
        "2. 实现 bank 冲突检测",
        "3. 验证：对比 behavior model 的 bank 访问模式",
    ],
    "pop_cnt": [
        "1. 实现位计数逻辑",
        "2. 验证：对所有输入模式计数正确",
    ],
    "memory_controller": [
        "1. 实现初始化 FSM",
        "2. 实现 refresh 定时器",
        "3. 实现命令调度 FSM",
        "4. 验证：对比 behavioral model 的状态序列",
    ],
    "dfi_sequencer": [
        "1. 实现命令时序延迟（tRCD, tRP, tRFC）",
        "2. 实现 DFI 输出映射",
        "3. 验证：对比 behavioral model 的 DFI 信号序列",
    ],
    "generic": [
        "1. 阅读 behavioral_reference，理解组件功能",
        "2. 实现状态寄存器初始化",
        "3. 实现组合逻辑",
        "4. 实现时序逻辑",
        "5. 实现停顿/冲刷/异常处理",
        "6. 验证：对比 behavior model 的输出",
    ],
}


@dataclass
class GenerateLoopPattern:
    """Generate loop pattern for multi-instance modules."""
    instance_name: str = ""
    loop_var: str = "i"
    loop_count: int = 1
    port_mapping: Dict[str, str] = field(default_factory=dict)
    description: str = ""


def _detect_generate_loops(pe: ProcessingElement,
                           arch: ArchDefinition) -> List[GenerateLoopPattern]:
    """从 PE 定义中检测 generate loop 模式。

    如果 PE 的 num_instances > 1，生成对应的 generate loop 模式。
    """
    patterns = []
    if pe.num_instances > 1:
        patterns.append(GenerateLoopPattern(
            instance_name=pe.name,
            loop_var=pe.instance_id_template,
            loop_count=pe.num_instances,
            description=f"{pe.name} × {pe.num_instances} instances",
        ))

    # Check for child PEs that should be generated in loops
    for child in pe.children:
        if child.num_instances > 1:
            patterns.append(GenerateLoopPattern(
                instance_name=child.name,
                loop_var=child.instance_id_template,
                loop_count=child.num_instances,
                description=f"{child.name} × {child.num_instances} instances",
            ))

    return patterns


# =====================================================================
# Handshake Interface Builder
# =====================================================================

def _build_handshake_interface(pe: ProcessingElement,
                               arch: ArchDefinition) -> Dict[str, Any]:
    """构建 PE 的 valid/ready 握手接口定义。

    从 interconnect 中检测 handshake 类型的连接，
    生成 valid/ready 信号对定义。
    """
    handshake_ports = []

    for conn in arch.interconnects:
        if conn.handshake is None:
            continue

        if conn.dst_pe == pe.name:
            # Input handshake
            handshake_ports.append({
                "direction": "input",
                "valid": f"{conn.src_pe}_{conn.handshake.valid_signal}",
                "ready": f"{pe.name}_{conn.handshake.ready_signal}",
                "from": conn.src_pe,
                "signals": [s.name for s in conn.signals],
            })
        if conn.src_pe == pe.name:
            # Output handshake
            handshake_ports.append({
                "direction": "output",
                "valid": f"{pe.name}_{conn.handshake.valid_signal}",
                "ready": f"{conn.dst_pe}_{conn.handshake.ready_signal}",
                "to": conn.dst_pe,
                "signals": [s.name for s in conn.signals],
            })

    return {"handshake_ports": handshake_ports}


# =====================================================================
# Queue/FIFO Interface Builder
# =====================================================================

def _build_queue_interface(pe: ProcessingElement,
                           arch: ArchDefinition) -> Dict[str, Any]:
    """构建 PE 的 FIFO 队列接口定义。"""
    queue_ports = []

    for conn in arch.interconnects:
        if conn.queue is None:
            continue

        if conn.dst_pe == pe.name:
            queue_ports.append({
                "direction": "input",
                "fifo_depth": conn.queue.depth,
                "from": conn.src_pe,
                "signals": [s.name for s in conn.signals],
            })
        if conn.src_pe == pe.name:
            queue_ports.append({
                "direction": "output",
                "fifo_depth": conn.queue.depth,
                "to": conn.dst_pe,
                "signals": [s.name for s in conn.signals],
            })

    return {"queue_ports": queue_ports}


# =====================================================================
# Golden Test Generator
# =====================================================================

def _gen_golden_tests(pe: ProcessingElement,
                      arch: ArchDefinition,
                      num_tests: int = 100) -> List[dict]:
    """从行为函数生成 golden 测试向量。"""
    import random
    tests = []

    for i in range(num_tests):
        inputs = {}
        for port in pe.inputs:
            if port.name in ("clk", "rst_n"):
                continue
            if port.width <= 1:
                inputs[port.name] = 1 if i == 0 else random.randint(0, 1)
            elif port.width <= 4:
                inputs[port.name] = random.randint(0, (1 << port.width) - 1)
            else:
                inputs[port.name] = random.randint(0, (1 << min(port.width, 16)) - 1)

        # Run behavioral reference
        if pe.behavior:
            ctx = CycleContext(inputs=inputs, model=arch.model)
            try:
                pe.behavior(ctx)
                tests.append({
                    "inputs": inputs,
                    "expected_outputs": dict(ctx.outputs),
                })
            except Exception:
                # If behavior fails, skip this test
                continue
        else:
            # No behavior function: use pass-through
            tests.append({
                "inputs": inputs,
                "expected_outputs": {p.name: inputs.get(p.name, 0)
                                     for p in pe.outputs},
            })

    # Ensure at least one reset test
    if pe.behavior:
        reset_inputs = {p.name: 0 for p in pe.inputs}
        reset_inputs["rst_n"] = 0
        ctx = CycleContext(inputs=reset_inputs, model=arch.model)
        try:
            pe.behavior(ctx)
            tests.insert(0, {
                "inputs": reset_inputs,
                "expected_outputs": dict(ctx.outputs),
            })
        except Exception:
            pass

    return tests


# =====================================================================
# Interconnect Interface Builder
# =====================================================================

def _build_interface(pe: ProcessingElement,
                     arch: ArchDefinition) -> Dict[str, Any]:
    """构建 PE 的互连接口定义。"""
    upstream = []
    downstream = []

    for conn in arch.interconnects:
        if conn.dst_pe == pe.name:
            entry = {
                "from": conn.src_pe,
                "signals": [s.name for s in conn.signals],
                "flow_type": conn.flow_type,
            }
            upstream.append(entry)
        if conn.src_pe == pe.name:
            entry = {
                "to": conn.dst_pe,
                "signals": [s.name for s in conn.signals],
                "flow_type": conn.flow_type,
            }
            downstream.append(entry)

    result = {"upstream": upstream, "downstream": downstream}

    # Add handshake interface details
    result.update(_build_handshake_interface(pe, arch))

    # Add queue interface details
    result.update(_build_queue_interface(pe, arch))

    return result


# =====================================================================
# Performance Target Extractor
# =====================================================================

def _extract_targets(pe: ProcessingElement,
                     arch: ArchDefinition) -> Dict[str, Any]:
    """从 PE 和架构提取性能目标。"""
    targets = {}

    if pe.latency > 0:
        targets["max_latency"] = pe.latency
    if pe.issue_width > 1:
        targets["min_throughput"] = pe.issue_width
    if pe.pe_type in ("alu", "mac_array"):
        targets["target_freq"] = 500e6
    if pe.pe_type in ("warp_scheduler", "cta_scheduler"):
        targets["min_ipc"] = pe.num_instances  # GPGPU: IPC scales with warp count
    if arch.ppa_targets:
        targets.update(arch.ppa_targets)

    return targets


# =====================================================================
# Sub-module Decomposition for Hierarchical PEs
# =====================================================================

def _build_submodule_decomposition(pe: ProcessingElement,
                                   arch: ArchDefinition) -> Dict[str, Any]:
    """构建子模块分解描述。

    对于有 children 的 PE，生成子模块实例化和互连描述。
    例如 cta_scheduler 分解为 5 个子模块。
    """
    if not pe.children:
        return {}

    submodules = []
    for child in pe.children:
        submodules.append({
            "name": child.name,
            "type": child.pe_type,
            "description": child.description,
            "instances": child.num_instances,
        })

    # Internal connections between children
    internal_conns = []
    for conn in arch.interconnects:
        src_is_child = any(c.name == conn.src_pe for c in pe.children)
        dst_is_child = any(c.name == conn.dst_pe for c in pe.children)
        if src_is_child and dst_is_child:
            internal_conns.append({
                "from": conn.src_pe,
                "to": conn.dst_pe,
                "signals": [s.name for s in conn.signals],
            })

    return {
        "submodules": submodules,
        "internal_connections": internal_conns,
    }


# =====================================================================
# Hierarchical Module Generation (Audit Fix 0522 — Section 2.4)
# =====================================================================

def _create_hierarchical_module(pe: ProcessingElement,
                                arch: ArchDefinition) -> Module:
    """Create a DSL Module that instantiates child PEs as submodules.

    Unlike `_create_base_module` which only creates ports and state vars,
    this function creates actual `SubmoduleInst` nodes for each child PE,
    connecting them via port-map generated from the arch interconnects.

    Returns a Module with:
      - Parent ports (from pe.inputs / pe.outputs)
      - Internal wires for inter-child connections
      - SubmoduleInst nodes for each child PE
    """
    module = Module(pe.name)
    module._type_name = pe.name

    # Clock and reset
    module.clk = Input(1, "clk")
    module.rst_n = Input(1, "rst_n")

    # Parent-level ports
    for port in pe.inputs:
        setattr(module, port.name, Input(port.width, port.name))
    for port in pe.outputs:
        setattr(module, port.name, Output(port.width, port.name))

    # State variables
    _declare_state_vars(module, pe.state)

    # Build a map of child PE name → ProcessingElement
    child_map: Dict[str, ProcessingElement] = {}
    for child in pe.children:
        child_map[child.name] = child

    # Create child skeleton modules and instantiate them
    for child in pe.children:
        child_mod = _create_base_module(child)
        _declare_state_vars(child_mod, child.state)
        inst_name = f"u_{child.name}"
        # Deduplicate if multiple instances
        existing = {n for n, _ in module._submodules}
        if inst_name in existing:
            i = 1
            while f"{inst_name}_{i}" in existing:
                i += 1
            inst_name = f"{inst_name}_{i}"

        # Build port_map: match child ports to parent signals by name
        port_map: Dict[str, Any] = {}
        port_map["clk"] = module.clk
        port_map["rst_n"] = module.rst_n

        # Try to connect child inputs/outputs to parent ports or internal wires
        for port in child.inputs:
            if port.name in ("clk", "rst_n"):
                continue
            if hasattr(module, port.name):
                val = getattr(module, port.name)
                if isinstance(val, (Input, Output, Wire, Reg)):
                    port_map[port.name] = val

        for port in child.outputs:
            if hasattr(module, port.name):
                val = getattr(module, port.name)
                if isinstance(val, (Input, Output, Wire, Reg)):
                    port_map[port.name] = val

        # Create intermediate wires for ports that don't match parent
        for port in child.inputs + child.outputs:
            if port.name not in port_map and port.name not in ("clk", "rst_n"):
                wire = Wire(port.width, f"{child.name}_{port.name}")
                setattr(module, f"{child.name}_{port.name}", wire)
                port_map[port.name] = wire

        inst = SubmoduleInst(inst_name, child_mod, {}, port_map)
        module._submodules.append((inst_name, child_mod))
        module._top_level.append(inst)

    # Create crossbar wires and connect child-to-child via interconnects
    for conn in arch.interconnects:
        src_is_child = conn.src_pe in child_map
        dst_is_child = conn.dst_pe in child_map
        if src_is_child and dst_is_child:
            for sig in conn.signals:
                wire_name = f"{conn.src_pe}_to_{conn.dst_pe}_{sig.name}"
                wire = Wire(sig.width, wire_name)
                setattr(module, wire_name, wire)
                # This wire will be connected in a later pass
                # (For now, the skeleton has the wire; the agent fills in logic)

    return module


# =====================================================================
# ArchSkeletonGenerator — Main Entry Point
# =====================================================================

class ArchSkeletonGenerator:
    """为 ArchDefinition 中的每个 PE 生成 AgentPackage。

    Skill-Guided Generation (参考 skills/skills-guided-gen.md):
      1. 生成模块骨架（端口 + 状态变量）
      2. 检索 skills 获取参考模式
      3. LogicGenerator 按 task 生成详细逻辑
      4. 失败则回退到硬编码骨架

    用法:
        gen = ArchSkeletonGenerator(skill_index_path="skills/gpgpu/skills_index.yaml")
        packages = gen.generate_all(arch)
        ifu_pkg = packages["IFU"]
    """

    def __init__(self, skill_index_path: Optional[str] = None,
                 enable_skill_guidance: bool = True,
                 enable_verifier: bool = True):
        self.skill_retriever = None
        self.logic_generator = None
        self.verifier = None
        if enable_skill_guidance and _SKILL_GUIDANCE_AVAILABLE:
            try:
                self.skill_retriever = SkillRetriever(skill_index_path)
                self.logic_generator = LogicGenerator()
                if enable_verifier:
                    self.verifier = Verifier()
            except Exception as e:
                # Skills not available — fall back to legacy mode
                self.skill_retriever = None
                self.logic_generator = None
                self.verifier = None

    def generate_all(self, arch: ArchDefinition) -> Dict[str, AgentPackage]:
        """为架构中每个 PE 生成 AgentPackage。"""
        packages = {}
        for pe in arch.processing_elements:
            packages[pe.name] = self._generate_package(pe, arch)
        return packages

    def _generate_package(self, pe: ProcessingElement,
                          arch: ArchDefinition) -> AgentPackage:
        # 0. Create structured ModuleRequirement (new)
        if _GEN_REQUIREMENT_AVAILABLE and ModuleRequirement is not None:
            module_req = ModuleRequirement.from_processing_element(pe, arch)
            behavior_req = extract_behavior_requirements(pe, arch)
        else:
            module_req = None
            behavior_req = None

        # 1. Create DSL Module with ports
        # If PE has children, create hierarchical module with actual SubmoduleInst nodes
        if pe.children:
            module = _create_hierarchical_module(pe, arch)
        else:
            module = _create_base_module(pe)
            # 2. Generate state variables (hierarchical module already does this)
            _declare_state_vars(module, pe.state)
            # (No logic filler — spec/DSL generation uses ArchDefinition + _SUBMODULE_DEFS directly)

        # 3. Generate golden tests
        golden_tests = _gen_golden_tests(pe, arch)

        # 4. Build interconnect interface (incl. handshake + queue)
        interface = _build_interface(pe, arch)

        # 5. Extract performance targets
        targets = _extract_targets(pe, arch)

        # 6. Generate implementation steps (GPGPU-aware)
        raw_steps = _TEMPLATE_STEPS.get(pe.pe_type, _TEMPLATE_STEPS["generic"])
        # Convert structured task dicts to human-readable strings
        steps = []
        for s in raw_steps:
            if isinstance(s, dict):
                steps.append(f"{s.get('name', 'task')}: {s.get('goal', '')}")
            else:
                steps.append(str(s))

        # 7. Use behavioral reference (or default pass-through)
        behavior = pe.behavior or self._default_behavior(pe)

        # 8. Detect generate-loop patterns
        gen_loops = _detect_generate_loops(pe, arch)

        # 9. Sub-module decomposition (descriptive info for agents)
        submod_info = _build_submodule_decomposition(pe, arch)

        # Store structured requirements on the AgentPackage for downstream use
        agent_pkg = AgentPackage(
            pe=pe,
            behavioral_reference=behavior,
            dsl_skeleton=module,
            golden_tests=golden_tests,
            performance_targets=targets,
            interconnect_interface=interface,
            implementation_steps=steps,
            generate_loops=gen_loops,
            submodule_decomposition=submod_info,
        )

        # Attach structured requirement dict (used by verification/roundtrip)
        if module_req is not None:
            agent_pkg._module_requirement = module_req.to_dict()
        if behavior_req is not None:
            agent_pkg._behavior_requirement = behavior_req

        return agent_pkg

    # (_fill_with_skill_guidance removed — spec/DSL generation uses ArchDefinition directly)

    def _build_generation_context(self, module_req, behavior_req,
                                   task, refs, summaries, module=None) -> "GenerationContext":
        """Build a structured GenerationContext for a single task.

        Combines:
        - ModuleRequirement (WHAT to build)
        - ReferenceSummaries (HOW similar things were built)
        - Sub-module decomposition (hierarchical structure)
        - Implementation steps (full task list for this PE type)
        - Skeleton state variables and logic hints
        - Coding rules and verification contract

        Args:
            module_req: ModuleRequirement for the target module
            behavior_req: Dict of behavior requirements
            task: Task dict from _TEMPLATE_STEPS
            refs: List[ReferenceCard] from SkillRetriever
            summaries: List[ReferenceSummary] from ReferenceExtractor
            module: Optional Module instance to extract skeleton state/logic

        Returns:
            GenerationContext ready for agent prompt or generator input
        """
        if not _GEN_REQUIREMENT_AVAILABLE or GenerationContext is None:
            return None

        from rtlgen.codegen import VerilogEmitter
        from rtlgen.gen_requirement import (
            TaskGenerationContext, SubModuleInfo, ImplementationStep,
        )

        # Build per-task context
        task_ctx = TaskGenerationContext(
            task_name=task.get("name", ""),
            task_goal=task.get("goal", ""),
            task_references=summaries,
            task_verification=task.get("verification", []),
            task_keywords=task.get("behavior_tags", []) + task.get("keywords", []),
        )

        # Build verification contract from task + requirement
        verification_contract = list(task.get("verification", []))
        if module_req and hasattr(module_req, "verification_hooks"):
            verification_contract.extend(module_req.verification_hooks)

        # Build coding rules tailored to this task
        coding_rules = list(self._DEFAULT_CODING_RULES)
        if behavior_req:
            for iface in behavior_req.get("interfaces", []):
                if "valid_ready" in iface:
                    coding_rules.append(
                        "use valid-ready fire condition for state transitions"
                    )

        # Extract sub-module decomposition from _SUBMODULE_DEFS
        sub_module_defs = _SUBMODULE_DEFS.get(module_req.pe_type, {}).get("submodules", [])
        sub_modules = []
        for sd in sub_module_defs:
            sub_modules.append(SubModuleInfo(
                name=sd.get("name", ""),
                submod_type=sd.get("type", ""),
                description=sd.get("description", ""),
                inputs=sd.get("inputs", []),
                outputs=sd.get("outputs", []),
            ))

        # Extract ALL implementation steps for this PE type
        all_tasks = [s for s in _TEMPLATE_STEPS.get(module_req.pe_type, [])
                     if isinstance(s, dict)]
        implementation_steps = []
        for t in all_tasks:
            implementation_steps.append(ImplementationStep(
                name=t.get("name", ""),
                goal=t.get("goal", ""),
                behavior_tags=t.get("behavior_tags", []),
                keywords=t.get("keywords", []),
            ))

        # Extract skeleton state variables from the module
        skeleton_state = []
        if module is not None:
            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(module, attr_name, None)
                if attr is None:
                    continue
                attr_type = type(attr).__name__
                if attr_type in ("Reg", "Wire", "Array"):
                    state_info = {"name": attr_name, "kind": attr_type}
                    if hasattr(attr, "width"):
                        state_info["width"] = attr.width
                    if hasattr(attr, "depth"):
                        state_info["depth"] = attr.depth
                    skeleton_state.append(state_info)

        gen_ctx = GenerationContext(
            target=module_req,
            reference_summaries=summaries,
            task_contexts=[task_ctx],
            coding_rules=coding_rules,
            verification_contract=verification_contract,
            sub_modules=sub_modules,
            implementation_steps=implementation_steps,
            skeleton_state_vars=skeleton_state,
        )
        gen_ctx.generation_task["hierarchy_mode"] = "hierarchical" if sub_modules else "leaf_only"
        return gen_ctx

    _DEFAULT_CODING_RULES: List[str] = [
        "use explicit registers for state",
        "use always_ff for sequential state",
        "use always_comb for combinational outputs",
        "no latches",
        "no multiple drivers",
        "reset all state registers",
    ]

    def _default_behavior(self, pe: ProcessingElement) -> Callable:
        """为没有行为函数的 PE 生成默认 pass-through 行为。

        先按名称匹配输入输出；名称不匹配时按位置一一映射。
        """
        input_names = [p.name for p in pe.inputs]

        def default_behavior(ctx: CycleContext):
            for port in pe.outputs:
                if port.name in ctx.inputs:
                    val = ctx.inputs[port.name]
                else:
                    # 按位置映射：第一个输入 -> 第一个输出
                    idx = pe.outputs.index(port)
                    if idx < len(input_names):
                        val = ctx.inputs.get(input_names[idx], 0)
                    else:
                        val = 0
                ctx.set_output(port.name, val)
        return default_behavior
