"""
skills.codec.video.arch_templates — xk265 H.265/HEVC Architecture Templates

Extensible architecture templates for xk265 H.265/HEVC encoder.
Architecture families: baseline, high_perf, low_power.
Full suite model: Xk265SuiteModel (all 38 modules).

Usage:
    from skills.codec.video.arch_templates import build_xk265_arch, Xk265SuiteModel

    # Quick build
    arch = build_xk265_arch(N=64, width=16)

    # Full suite simulation
    suite = Xk265SuiteModel(lcu_size=64, pic_width=1920, pic_height=1080)
    suite.run(num_cycles=1000)
"""
from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from rtlgen import (
    ProcessingElement, PortDesc, StateDesc,
    ArchDefinition, InterconnectSpec, ModelProvider,
    TemplateRegistry,
)

# Import behaviors to register codec templates in TemplateRegistry
import skills.codec.video.behaviors  # noqa: F401
from skills.codec.video.models import (
    H265EncoderModel, Xk265SuiteModel,
    EncCtrlModel,
)


# =====================================================================
# Architecture Model Provider
# =====================================================================

class Codec_Model(ModelProvider):
    """Codec behavioral model for H.265 encoder simulation."""
    model_type = "codec"

    def __init__(self, lcu_size: int = 64, pic_width: int = 1920,
                 pic_height: int = 1080, qp: int = 22, max_cu_depth: int = 3):
        self.encoder = H265EncoderModel(
            lcu_size=lcu_size, pic_width=pic_width, pic_height=pic_height,
        )
        self.encoder.configure(qp=qp, max_cu_depth=max_cu_depth)

    def on_cycle(self, cycle: int):
        pass

    def get_service(self, name: str, **kwargs) -> Any:
        if name == "encoder_status":
            return self.encoder.get_status()
        if name == "run_ctu":
            return self.encoder.run(num_cycles=kwargs.get("cycles", 100))
        return None


# =====================================================================
# Architecture Parameters
# =====================================================================

@dataclass
class CodecArchParams:
    """H.265 encoder architecture parameters."""
    name: str = "h265_encoder"
    description: str = ""

    # CTU configuration
    lcu_size: int = 64
    max_cu_depth: int = 3
    min_cu_size: int = 8

    # Pixel / coefficient widths
    pixel_width: int = 8
    coeff_width: int = 16

    # Motion estimation
    ime_search_range: int = 64
    fme_refinement_range: int = 2

    # Intra prediction
    num_intra_modes: int = 35

    # Cost widths
    ime_cost_width: int = 28
    posi_cost_width: int = 20
    fme_cost_width: int = 20

    # CABAC
    cabac_engine: str = "pipe"

    # Picture dimensions
    pic_width: int = 1920
    pic_height: int = 1080

    # PPA targets
    target_mhz: int = 300
    max_area_mm2: float = 5.0
    max_power_mw: float = 500.0

    # Simulation
    sim_cycles: int = 500

    # Output
    output_dir: str = ""

    def __post_init__(self):
        self.min_cu_size = self.lcu_size // (1 << self.max_cu_depth)


# =====================================================================
# PE Builder
# =====================================================================

@dataclass
class CodecPeBuilder:
    """Named PE builder for codec components."""
    name: str
    pe_type: str
    behavior_fn: Callable[[], Callable]
    inputs: List[PortDesc]
    outputs: List[PortDesc]
    state: List[StateDesc] = field(default_factory=list)
    description: str = ""

    def build(self) -> ProcessingElement:
        return ProcessingElement(
            name=self.name, pe_type=self.pe_type,
            description=self.description,
            behavior=self.behavior_fn(),
            inputs=copy.deepcopy(self.inputs),
            outputs=copy.deepcopy(self.outputs),
            state=copy.deepcopy(self.state),
        )


def _ins(name: str, width: int = 1) -> PortDesc:
    return PortDesc(name=name, direction="input", width=width)


def _out(name: str, width: int = 1) -> PortDesc:
    return PortDesc(name=name, direction="output", width=width)


# =====================================================================
# Codec PE Catalog
# =====================================================================

class CodecPeCatalog:
    """Pre-defined PE builders for xk265 encoder components."""

    @staticmethod
    def enc_ctrl(params: CodecArchParams) -> CodecPeBuilder:
        return CodecPeBuilder(
            name="enc_ctrl", pe_type="fsm_controller",
            description="Top-level encoder FSM: CTU raster-scan sequencing",
            behavior_fn=lambda: TemplateRegistry.get("enc_ctrl")(num_pipeline_stages=8),
            inputs=[
                _ins("clk"), _ins("rst_n"),
                _ins("sys_start_i"), _ins("sys_slice_type_i"),
                _ins("sys_total_x_i", 6), _ins("sys_total_y_i", 6),
                _ins("frame_width_remain_i", 6), _ins("frame_height_remain_i", 6),
                _ins("prei_done_i"), _ins("posi_done_i"),
                _ins("ime_done_i"), _ins("fme_done_i"),
                _ins("rec_done_i"), _ins("db_done_i"),
                _ins("cabac_done_i"), _ins("fetch_done_i"),
            ],
            outputs=[
                _out("sys_done_o"),
                _out("prei_start_o"), _out("posi_start_o"),
                _out("ime_start_o"), _out("fme_start_o"),
                _out("rec_start_o"), _out("db_start_o"),
                _out("cabac_start_o"), _out("fetch_start_o"),
                _out("ctu_x_cur_o", 6), _out("ctu_y_cur_o", 6),
                _out("rc_qp_o", 6),
            ],
            state=[
                StateDesc("state", "int", "FSM state"),
                StateDesc("ctu_x", "int", "Current CTU X"),
                StateDesc("ctu_y", "int", "Current CTU Y"),
            ],
        )

    @staticmethod
    def prei_top(params: CodecArchParams) -> CodecPeBuilder:
        return CodecPeBuilder(
            name="prei_top", pe_type="prei_processor",
            description="Pre-intra estimation: gradient + mode decision + rate control",
            behavior_fn=lambda: TemplateRegistry.get("prei_processor")(
                lcu_size=params.lcu_size, pixel_width=params.pixel_width),
            inputs=[
                _ins("clk"), _ins("rst_n"), _ins("start_i"),
                _ins("ctu_x_i", 6), _ins("ctu_y_i", 6),
                _ins("md_data_i", params.pixel_width * 32),
                _ins("actual_bitnum_i", 16),
                _ins("reg_initial_qp", 6), _ins("reg_max_qp", 6),
                _ins("reg_min_qp", 6), _ins("reg_delta_qp", 6),
                _ins("reg_lcu_rc_en"),
            ],
            outputs=[
                _out("done_o"), _out("rc_qp_o", 6),
                _out("md_ren_o"), _out("md_sel_o"),
                _out("md_size_o", 2), _out("md_4x4_x_o", 4),
                _out("md_4x4_y_o", 4), _out("md_idx_o", 5),
                _out("md_we_o"), _out("md_waddr_o", 7),
                _out("md_wdata_o", 6),
            ],
            state=[
                StateDesc("active", "int", "Processing active"),
                StateDesc("cnt", "int", "Pixel counter"),
            ],
        )

    @staticmethod
    def posi_top(params: CodecArchParams) -> CodecPeBuilder:
        return CodecPeBuilder(
            name="posi_top", pe_type="posi_processor",
            description="Intra prediction search: SATD cost + partition decision",
            behavior_fn=lambda: TemplateRegistry.get("posi_processor")(
                lcu_size=params.lcu_size, cu_depth=params.max_cu_depth,
                num_modes=params.num_intra_modes, cost_width=params.posi_cost_width),
            inputs=[
                _ins("clk"), _ins("rst_n"), _ins("start_i"),
                _ins("sys_posi4x4bit_i", 5), _ins("num_mode_i", 3),
                _ins("ctu_x_all_i", 6), _ins("ctu_y_all_i", 6),
                _ins("ctu_x_res_i", 4), _ins("ctu_y_res_i", 4),
                _ins("ctu_x_cur_i", 6), _ins("ctu_y_cur_i", 6),
                _ins("qp_i", 6), _ins("mod_rd_dat_i", 6),
                _ins("ori_rd_dat_i", params.pixel_width * 32),
            ],
            outputs=[
                _out("done_o"), _out("mod_rd_ena_o"),
                _out("mod_rd_adr_o", 9), _out("ori_rd_ena_o"),
                _out("ori_rd_sel_o", 2), _out("ori_rd_siz_o", 2),
                _out("ori_rd_4x4_x_o", 4), _out("ori_rd_4x4_y_o", 4),
                _out("ori_rd_idx_o", 5), _out("mod_wr_ena_o"),
                _out("mod_wr_adr_o", 8), _out("mod_wr_dat_o", 6),
                _out("partition_o", 85), _out("cost_o", params.posi_cost_width),
            ],
            state=[
                StateDesc("active", "int", "Processing active"),
                StateDesc("block_cnt", "int", "Block counter"),
                StateDesc("mode_cnt", "int", "Mode counter"),
                StateDesc("best_cost", "int", "Best SATD cost"),
            ],
        )

    @staticmethod
    def ime_top(params: CodecArchParams) -> CodecPeBuilder:
        return CodecPeBuilder(
            name="ime_top", pe_type="ime_processor",
            description="Integer motion estimation: multi-scale SAD + partition",
            behavior_fn=lambda: TemplateRegistry.get("ime_processor")(
                lcu_size=params.lcu_size, search_range=params.ime_search_range,
                cost_width=params.ime_cost_width),
            inputs=[
                _ins("clk"), _ins("rst_n"), _ins("start_i"),
                _ins("cmd_num_i", 3), _ins("cmd_dat_i", 232),
                _ins("qp_i", 6),
                _ins("ctu_x_all_i", 6), _ins("ctu_y_all_i", 6),
                _ins("ctu_x_res_i", 6), _ins("ctu_y_res_i", 6),
                _ins("ctu_x_cur_i", 6), _ins("ctu_y_cur_i", 6),
                _ins("ori_dat_i", params.pixel_width * 32),
                _ins("ref_hor_dat_i", params.pixel_width * 32),
                _ins("ref_ver_dat_i", params.pixel_width * 32),
            ],
            outputs=[
                _out("done_o"), _out("downsample_o"),
                _out("ori_ena_o"), _out("ori_adr_x_o", 6),
                _out("ori_adr_y_o", 6), _out("ref_hor_ena_o"),
                _out("ref_hor_adr_x_o", 8), _out("ref_hor_adr_y_o", 7),
                _out("ref_ver_ena_o"), _out("ref_ver_adr_x_o", 7),
                _out("ref_ver_adr_y_o", 8), _out("partition_o", 42),
                _out("mv_wr_ena_o"), _out("mv_wr_adr_o", 6),
                _out("mv_wr_dat_o", 13),
            ],
            state=[
                StateDesc("phase", "int", "Processing phase"),
                StateDesc("best_sad", "int", "Best SAD value"),
                StateDesc("best_mv_x", "int", "Best MV X"),
                StateDesc("best_mv_y", "int", "Best MV Y"),
            ],
        )

    @staticmethod
    def fme_top(params: CodecArchParams) -> CodecPeBuilder:
        return CodecPeBuilder(
            name="fme_top", pe_type="fme_processor",
            description="Fractional motion estimation: 1/4-pel refinement",
            behavior_fn=lambda: TemplateRegistry.get("fme_processor")(
                lcu_size=params.lcu_size, cost_width=params.fme_cost_width),
            inputs=[
                _ins("clk"), _ins("rst_n"), _ins("start_i"),
                _ins("ctu_x_cur_i", 6), _ins("ctu_y_cur_i", 6),
                _ins("qp_i", 6), _ins("partition_i", 42),
                _ins("mv_rd_dat_i", 20),
                _ins("cur_dat_i", params.pixel_width * 32),
                _ins("ref_dat_i", params.pixel_width * 64),
            ],
            outputs=[
                _out("done_o"), _out("mv_rd_ena_o"),
                _out("mv_rd_adr_o", 6), _out("cur_rd_ena_o"),
                _out("cur_rd_adr_o", 8), _out("ref_rd_ena_o"),
                _out("ref_rd_adr_o", 8), _out("fme_partition_o", 42),
                _out("fme_mv_o", 20),
            ],
            state=[
                StateDesc("phase", "int", "Processing phase"),
                StateDesc("best_cost", "int", "Best FME cost"),
            ],
        )

    @staticmethod
    def rec_top(params: CodecArchParams) -> CodecPeBuilder:
        num_4x4 = (params.lcu_size // 4) ** 2
        return CodecPeBuilder(
            name="rec_top", pe_type="rec_processor",
            description="Reconstruction: intra prediction + motion comp + TQ",
            behavior_fn=lambda: TemplateRegistry.get("rec_processor")(
                lcu_size=params.lcu_size, coeff_width=params.coeff_width),
            inputs=[
                _ins("clk"), _ins("rst_n"),
                _ins("sys_start_i"), _ins("start_i"),
                _ins("ctu_x_all_i", 6), _ins("ctu_y_all_i", 6),
                _ins("ctu_x_res_i", 4), _ins("ctu_y_res_i", 4),
                _ins("ctu_x_cur_i", 6), _ins("ctu_y_cur_i", 6),
                _ins("qp_i", 6), _ins("type_i"),
                _ins("intra_partition_i", 85), _ins("inter_partition_i", 42),
                _ins("rec_skip_flag_i", num_4x4),
                _ins("md_rd_dat_i", 6), _ins("cur_rd_dat_i", params.pixel_width * 32),
                _ins("mv_rd_dat_i", 20), _ins("ref_rd_dat_i", params.pixel_width * 8),
                _ins("pre_fme_rd_dat_i", params.pixel_width * 32),
            ],
            outputs=[
                _out("done_o"), _out("md_rd_ena_o"), _out("md_rd_adr_o", 8),
                _out("cur_rd_ena_o"), _out("cur_rd_sel_o", 2),
                _out("cur_rd_siz_o", 2), _out("cur_rd_4x4_x_o", 4),
                _out("cur_rd_4x4_y_o", 4), _out("cur_rd_idx_o", 5),
                _out("mv_rd_ena_o"), _out("mv_rd_adr_o", 6),
                _out("ref_rd_ena_o"), _out("ref_rd_sel_o", 2),
                _out("ref_rd_idx_x_o", 8), _out("ref_rd_idx_y_o", 8),
                _out("pre_fme_rd_ena_o"), _out("pre_fme_wr_ena_o"),
                _out("pre_fme_wr_dat_o", params.pixel_width * 32),
                _out("rec_rd_dat_o", params.pixel_width * 32),
                _out("cef_rd_dat_o", params.coeff_width * 32),
                _out("mvd_rd_dat_o", 23),
                _out("cbf_y_o", num_4x4), _out("cbf_u_o", num_4x4),
                _out("cbf_v_o", num_4x4),
                _out("fme_IinP_flag_o", 4), _out("IinP_flag_o", 3),
            ],
            state=[StateDesc("phase", "int", "Processing phase")],
        )

    @staticmethod
    def dbsao_top(params: CodecArchParams) -> CodecPeBuilder:
        num_4x4 = (params.lcu_size // 4) ** 2
        return CodecPeBuilder(
            name="dbsao_top", pe_type="dbsao_processor",
            description="Deblocking filter + Sample Adaptive Offset",
            behavior_fn=lambda: TemplateRegistry.get("dbsao_processor")(lcu_size=params.lcu_size),
            inputs=[
                _ins("clk"), _ins("rst_n"),
                _ins("sys_ctu_x_i", 6), _ins("sys_ctu_y_i", 6),
                _ins("sys_db_ena_i"), _ins("sys_sao_ena_i"),
                _ins("sys_start_i"), _ins("rc_qp_i", 6),
                _ins("IinP_flag_i", 3), _ins("mb_type_i"),
                _ins("mb_partition_i", 21), _ins("mb_p_pu_mode_i", 42),
                _ins("mb_cbf_i", num_4x4), _ins("mb_cbf_u_i", num_4x4),
                _ins("mb_cbf_v_i", num_4x4), _ins("mb_mv_rdata_i", 20),
                _ins("rec_rd_pxl_i", params.pixel_width * 32),
                _ins("ori_pxl_i", params.pixel_width * 32),
                _ins("top_rdata_i", 32),
            ],
            outputs=[
                _out("sys_done_o"), _out("mb_mv_ren_o"),
                _out("mb_mv_raddr_o", 6), _out("rec_rd_ren_o"),
                _out("rec_rd_sel_o", 2), _out("rec_rd_siz_o", 2),
                _out("rec_rd_4x4_x_o", 4), _out("rec_rd_4x4_y_o", 4),
                _out("rec_rd_4x4_idx_o", 5), _out("rec_wr_wen_o"),
                _out("rec_wr_sel_o", 2), _out("rec_wr_siz_o", 2),
                _out("rec_wr_4x4_x_o", 4), _out("rec_wr_4x4_y_o", 4),
                _out("rec_wr_4x4_idx_o", 5), _out("rec_wr_pxl_o", params.pixel_width * 32),
                _out("ori_ren_o"), _out("fetch_wen_o"),
                _out("fetch_wdata_o", 128), _out("top_ren_o"),
                _out("sao_data_o", 62),
            ],
            state=[StateDesc("phase", "int", "Processing phase")],
        )

    @staticmethod
    def cabac_top(params: CodecArchParams) -> CodecPeBuilder:
        num_4x4 = (params.lcu_size // 4) ** 2
        return CodecPeBuilder(
            name="cabac_top", pe_type="cabac_processor",
            description="CABAC entropy coding: binarization + context model + arithmetic encode",
            behavior_fn=lambda: TemplateRegistry.get("cabac_processor")(lcu_size=params.lcu_size),
            inputs=[
                _ins("clk"), _ins("rst_n"),
                _ins("sys_slice_type_i"), _ins("sys_total_x_i", 6),
                _ins("sys_total_y_i", 6), _ins("sys_mb_x_i", 6),
                _ins("sys_mb_y_i", 6), _ins("frame_width_remain_i", 6),
                _ins("frame_height_remain_i", 6), _ins("sys_start_i"),
                _ins("rc_qp_i", 6), _ins("rc_param_qp_i", 6),
                _ins("sao_i", 62), _ins("mb_partition_i", 85),
                _ins("mb_p_pu_mode_i", 42), _ins("mb_skip_flag_i", 85),
                _ins("mb_merge_flag_i", 85), _ins("mb_merge_idx_i", 340),
                _ins("mb_cbf_y_i", num_4x4), _ins("mb_cbf_u_i", num_4x4),
                _ins("mb_cbf_v_i", num_4x4), _ins("mb_i_luma_mode_data_i", 6),
                _ins("mb_mvd_data_i", 15), _ins("mb_cef_data_i", 512),
            ],
            outputs=[
                _out("cabac_done_o"), _out("bs_data_o", 8), _out("bs_val_o"),
                _out("slice_done_o"), _out("mb_i_luma_mode_ren_o"),
                _out("mb_i_luma_mode_addr_o", 6), _out("mb_mvd_ren_o"),
                _out("mb_mvd_addr_o", 6), _out("ec_coe_rd_ena_o"),
                _out("ec_coe_rd_sel_o", 2), _out("ec_coe_rd_siz_o", 2),
                _out("ec_coe_rd_4x4_x_o", 4), _out("ec_coe_rd_4x4_y_o", 4),
                _out("ec_coe_rd_idx_o", 5),
            ],
            state=[
                StateDesc("active", "int", "Encoding active"),
                StateDesc("blk_cnt", "int", "Block counter"),
            ],
        )

    @staticmethod
    def fetch_top(params: CodecArchParams) -> CodecPeBuilder:
        return CodecPeBuilder(
            name="fetch_top", pe_type="fetch_processor",
            description="Memory interface: pixel buffer management + external memory access",
            behavior_fn=lambda: TemplateRegistry.get("fetch_processor")(
                lcu_size=params.lcu_size, pixel_width=params.pixel_width),
            inputs=[
                _ins("clk"), _ins("rst_n"),
                _ins("sysif_type_i"), _ins("sys_ctu_all_x_i", 6),
                _ins("sys_ctu_all_y_i", 6), _ins("sys_all_x_i", 13),
                _ins("sys_all_y_i", 12), _ins("sysif_start_i"),
            ],
            outputs=[
                _out("sysif_done_o"),
                _out("prei_cur_pel_o", params.pixel_width * 32),
                _out("posi_cur_pel_o", params.pixel_width * 32),
                _out("ime_cur_pel_o", params.pixel_width * 32),
                _out("ime_ref_pel_o", params.pixel_width * 32),
                _out("fme_cur_pel_o", params.pixel_width * 32),
                _out("fme_ref_pel_o", params.pixel_width * 64),
                _out("rec_cur_pel_o", params.pixel_width * 32),
                _out("rec_ref_pel_o", params.pixel_width * 8),
                _out("db_cur_pel_o", params.pixel_width * 32),
                _out("db_rdata_o", 32),
                _out("extif_start_o"), _out("extif_mode_o", 5),
                _out("extif_x_o", 12), _out("extif_y_o", 12),
                _out("extif_width_o", 8), _out("extif_height_o", 8),
                _out("extif_data_o", 128),
            ],
            state=[
                StateDesc("active", "int", "Transfer active"),
                StateDesc("burst_cnt", "int", "Burst counter"),
            ],
        )


# =====================================================================
# Base Architecture Template
# =====================================================================

class CodecArchTemplate(ABC):
    """Base class for codec architecture templates."""

    def __init__(self, params: CodecArchParams):
        self.params = params
        self.pe_catalog = CodecPeCatalog()

    @property
    @abstractmethod
    def family_name(self) -> str:
        ...

    def build_pes(self) -> List[ProcessingElement]:
        return [
            self.pe_catalog.enc_ctrl(self.params).build(),
            self.pe_catalog.prei_top(self.params).build(),
            self.pe_catalog.posi_top(self.params).build(),
            self.pe_catalog.ime_top(self.params).build(),
            self.pe_catalog.fme_top(self.params).build(),
            self.pe_catalog.rec_top(self.params).build(),
            self.pe_catalog.dbsao_top(self.params).build(),
            self.pe_catalog.cabac_top(self.params).build(),
            self.pe_catalog.fetch_top(self.params).build(),
        ]

    def build_interconnects(self) -> List[InterconnectSpec]:
        num_4x4 = (self.params.lcu_size // 4) ** 2
        return [
            InterconnectSpec(src_pe="enc_ctrl", dst_pe="prei_top",
                             signals=[_out("start")], flow_type="stream"),
            InterconnectSpec(src_pe="enc_ctrl", dst_pe="posi_top",
                             signals=[_out("start")], flow_type="stream"),
            InterconnectSpec(src_pe="enc_ctrl", dst_pe="ime_top",
                             signals=[_out("start")], flow_type="stream"),
            InterconnectSpec(src_pe="enc_ctrl", dst_pe="fme_top",
                             signals=[_out("start")], flow_type="stream"),
            InterconnectSpec(src_pe="enc_ctrl", dst_pe="rec_top",
                             signals=[_out("start")], flow_type="stream"),
            InterconnectSpec(src_pe="enc_ctrl", dst_pe="dbsao_top",
                             signals=[_out("start")], flow_type="stream"),
            InterconnectSpec(src_pe="enc_ctrl", dst_pe="cabac_top",
                             signals=[_out("start")], flow_type="stream"),
            InterconnectSpec(src_pe="enc_ctrl", dst_pe="fetch_top",
                             signals=[_out("start")], flow_type="stream"),
            InterconnectSpec(src_pe="posi_top", dst_pe="rec_top",
                             signals=[_out("partition", 85)], flow_type="stream"),
            InterconnectSpec(src_pe="ime_top", dst_pe="fme_top",
                             signals=[_out("partition", 42)], flow_type="stream"),
            InterconnectSpec(src_pe="ime_top", dst_pe="rec_top",
                             signals=[_out("partition", 42)], flow_type="stream"),
            InterconnectSpec(src_pe="fme_top", dst_pe="rec_top",
                             signals=[_out("partition", 42), _out("mv", 20)], flow_type="stream"),
            InterconnectSpec(src_pe="rec_top", dst_pe="dbsao_top",
                             signals=[_out("cbf_y", num_4x4), _out("cbf_u", num_4x4),
                                      _out("cbf_v", num_4x4), _out("IinP", 3)], flow_type="stream"),
            InterconnectSpec(src_pe="dbsao_top", dst_pe="cabac_top",
                             signals=[_out("sao_data", 62)], flow_type="stream"),
        ]

    def build(self) -> ArchDefinition:
        pes = self.build_pes()
        interconnects = self.build_interconnects()
        description = (
            f"{self.family_name} — H.265/HEVC encoder, "
            f"LCU={self.params.lcu_size}, depth={self.params.max_cu_depth}, "
            f"{self.params.pic_width}x{self.params.pic_height}"
        )
        arch = ArchDefinition(
            name=self.params.name, description=description,
            isa="stream", processing_elements=pes,
            interconnects=interconnects,
            ppa_targets={
                "target_clock_mhz": self.params.target_mhz,
                "max_area_mm2": self.params.max_area_mm2,
                "max_power_mw": self.params.max_power_mw,
            },
        )
        codec_model = Codec_Model(
            lcu_size=self.params.lcu_size, pic_width=self.params.pic_width,
            pic_height=self.params.pic_height, qp=22,
            max_cu_depth=self.params.max_cu_depth,
        )
        arch.model = codec_model
        return arch


# =====================================================================
# Concrete Templates
# =====================================================================

class BaselineCodecTemplate(CodecArchTemplate):
    """Standard xk265 8-stage pipeline (reference design)."""

    @property
    def family_name(self) -> str:
        return "Baseline H.265 Encoder"


class HighPerfCodecTemplate(CodecArchTemplate):
    """High-performance dual-pipeline encoder."""

    @property
    def family_name(self) -> str:
        return "High-Performance H.265 Encoder"

    def build_pes(self) -> List[ProcessingElement]:
        pes = super().build_pes()
        ime2 = self.pe_catalog.ime_top(self.params)
        ime2.name = "ime_top_2"
        pes.append(ime2.build())
        fme2 = self.pe_catalog.fme_top(self.params)
        fme2.name = "fme_top_2"
        pes.append(fme2.build())
        return pes


class LowPowerCodecTemplate(CodecArchTemplate):
    """Low-power simplified encoder."""

    @property
    def family_name(self) -> str:
        return "Low-Power H.265 Encoder"

    def __init__(self, params: CodecArchParams):
        params.ime_search_range = 32
        params.num_intra_modes = 9
        super().__init__(params)


# =====================================================================
# Convenience Functions
# =====================================================================

def build_xk265_arch(lcu_size: int = 64, max_cu_depth: int = 3,
                     pic_width: int = 1920, pic_height: int = 1080,
                     target_mhz: int = 300) -> ArchDefinition:
    """Build the default xk265 encoder architecture.

    Args:
        lcu_size: Largest coding unit size (64/32/16)
        max_cu_depth: Quad-tree depth (0=LCU only, 3=8x8 min)
        pic_width: Picture width in pixels
        pic_height: Picture height in pixels
        target_mhz: Target clock frequency in MHz

    Returns:
        ArchDefinition with 9 PEs and 14 interconnects.
    """
    params = CodecArchParams(
        lcu_size=lcu_size, max_cu_depth=max_cu_depth,
        pic_width=pic_width, pic_height=pic_height,
        target_mhz=target_mhz,
    )
    return BaselineCodecTemplate(params).build()


# =====================================================================
# Template Registry
# =====================================================================

_template_registry: Dict[str, type] = {}


def register_template(name: str, template_cls: type):
    _template_registry[name] = template_cls


def get_template(name: str) -> Optional[type]:
    return _template_registry.get(name)


def list_templates() -> List[str]:
    return list(_template_registry.keys())


register_template("baseline", BaselineCodecTemplate)
register_template("high_perf", HighPerfCodecTemplate)
register_template("low_power", LowPowerCodecTemplate)
