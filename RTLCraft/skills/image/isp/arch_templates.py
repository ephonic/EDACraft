"""
skills.image.isp.arch_templates — ISP Architecture Templates

Provides:
  - build_isp_arch() to create ProcessingElements for the full ISP pipeline
"""
from __future__ import annotations

from typing import Dict, List, Optional

from rtlgen.arch_def import (
    InterconnectSpec,
    PortDesc,
    ProcessingElement,
    StateDesc,
    ArchDefinition,
    ModelProvider,
)
from skills.image.isp.behaviors import (
    isp_axi_in_template,
    isp_crop_template,
    isp_dpc_template,
    isp_blc_template,
    isp_oecf_template,
    isp_dg_template,
    isp_lsc_template,
    isp_bnr_template,
    isp_wb_template,
    isp_awb_stats_template,
    isp_demosaic_template,
    isp_ccm_template,
    isp_gamma_template,
    isp_ae_stats_template,
    isp_csc_template,
    isp_ldci_template,
    isp_sharpen_template,
    isp_nr2d_template,
    isp_scale_template,
    isp_yuv_template,
    isp_axi_out_template,
    isp_apb_regs_template,
)
from skills.image.isp.models import ISPModel


class ISP_Model(ModelProvider):
    """Model provider for ISP architecture."""

    name = "isp_model"
    description = "ISP pipeline golden-reference model (Bayer→RGB→YUV)"

    def create_behavior(self, **kwargs):
        return ISPModel().create_behavior(**kwargs)

    def create_testbench(self, **kwargs) -> List[Dict]:
        return ISPModel().create_testbench(**kwargs)


def build_isp_arch(
    design_name: str = "isp_pipeline",
    raw_width: int = 12,
    rgb_width: int = 12,
    yuv_width: int = 8,
    max_width: int = 2592,
    max_height: int = 1536,
    num_regs: int = 32,
    output_width: int = 24,
) -> ArchDefinition:
    """Build an ArchDefinition for the ISP pipeline.

    Creates 22 ProcessingElements matching the hardware hierarchy:
      Bayer: AXIIn, Crop, DPC, BLC, OECF, DG, LSC, BNR, WB
      RGB:   AWBStats, Demosaic, CCM, Gamma
      YUV:   AEStats, CSC, LDCI, Sharpen, NR2D, Scale, YUV
      IO:    AXIOut, APBRegs
    """
    pes: List[ProcessingElement] = []

    # =========================================================================
    # Bayer Domain
    # =========================================================================

    # 1. ISPAXIStreamIn
    pes.append(ProcessingElement(
        name="ISPAXIStreamIn",
        pe_type="isp_axi_in",
        description="AXI-Stream slave input with 2-stage FIFO pipeline",
        inputs=[
            PortDesc("s_axis_tvalid", 1),
            PortDesc("s_axis_tdata", raw_width),
            PortDesc("s_axis_tlast", 1),
            PortDesc("s_axis_tuser", 1),
            PortDesc("m_axis_tready", 1),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_data_o", raw_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
            PortDesc("s_axis_tready", 1),
        ],
        state=[
            StateDesc("fifo0", raw_width),
            StateDesc("valid0", 1),
            StateDesc("fifo1", raw_width),
            StateDesc("valid1", 1),
            StateDesc("tready", 1),
            StateDesc("sof0", 1),
            StateDesc("eol0", 1),
        ],
        behavior=isp_axi_in_template(),
    ))

    # 2. ISPCrop
    pes.append(ProcessingElement(
        name="ISPCrop",
        pe_type="isp_crop",
        description="Configurable window cropping with x/y region gating",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_data_i", raw_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_start_x", 16),
            PortDesc("cfg_start_y", 16),
            PortDesc("cfg_width", 16),
            PortDesc("cfg_height", 16),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_data_o", raw_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("x_cnt", 16),
            StateDesc("y_cnt", 16),
        ],
        behavior=isp_crop_template(max_width=max_width, max_height=max_height),
    ))

    # 3. ISPDPC
    pes.append(ProcessingElement(
        name="ISPDPC",
        pe_type="isp_dpc",
        description="5x5 dynamic dead pixel correction with 8-direction gradient",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_data_i", raw_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_threshold", 16),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_data_o", raw_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("center_buf", raw_width),
            StateDesc("ring_buf", 8 * raw_width),
            StateDesc("out_valid", 1),
            StateDesc("out_sof", 1),
            StateDesc("out_eol", 1),
        ],
        behavior=isp_dpc_template(raw_width=raw_width),
    ))

    # 4. ISPBLC
    pes.append(ProcessingElement(
        name="ISPBLC",
        pe_type="isp_blc",
        description="Per-channel Bayer black level offset correction",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_data_i", raw_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_r_offset", 12),
            PortDesc("cfg_gr_offset", 12),
            PortDesc("cfg_gb_offset", 12),
            PortDesc("cfg_b_offset", 12),
            PortDesc("cfg_bayer", 2),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_data_o", raw_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("row", 1),
            StateDesc("col", 1),
        ],
        behavior=isp_blc_template(raw_width=raw_width),
    ))

    # 5. ISPOECF
    pes.append(ProcessingElement(
        name="ISPOECF",
        pe_type="isp_oecf",
        description="Opto-electronic conversion function: 256-entry per-channel LUT",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_data_i", raw_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_data_o", raw_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("oecf_lut_0", 12),
            StateDesc("oecf_lut_1", 12),
            StateDesc("oecf_lut_2", 12),
            StateDesc("oecf_lut_3", 12),
            # ... 256 entries total, listed 4 for skeleton
        ],
        behavior=isp_oecf_template(raw_width=raw_width),
    ))

    # 6. ISPDG
    pes.append(ProcessingElement(
        name="ISPDG",
        pe_type="isp_dg",
        description="Digital gain: Q4.8 fixed-point with saturation clip",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_data_i", raw_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_gain", 12),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_data_o", raw_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[],
        behavior=isp_dg_template(raw_width=raw_width),
    ))

    # 7. ISPLSC
    pes.append(ProcessingElement(
        name="ISPLSC",
        pe_type="isp_lsc",
        description="Lens shading correction: per-channel radial Q4.4 gain",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_data_i", raw_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_gain_r", 8),
            PortDesc("cfg_gain_gr", 8),
            PortDesc("cfg_gain_gb", 8),
            PortDesc("cfg_gain_b", 8),
            PortDesc("cfg_bayer", 2),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_data_o", raw_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("row", 1),
            StateDesc("col", 1),
        ],
        behavior=isp_lsc_template(raw_width=raw_width),
    ))

    # 8. ISPBNR
    pes.append(ProcessingElement(
        name="ISPBNR",
        pe_type="isp_bnr",
        description="Bayer noise reduction: joint bilateral filter with green guiding",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_data_i", raw_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_data_o", raw_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("center_buf", raw_width),
            StateDesc("neighbors", 8 * raw_width),
            StateDesc("out_valid", 1),
            StateDesc("out_sof", 1),
            StateDesc("out_eol", 1),
        ],
        behavior=isp_bnr_template(raw_width=raw_width),
    ))

    # 9. ISPWB
    pes.append(ProcessingElement(
        name="ISPWB",
        pe_type="isp_wb",
        description="White balance: Bayer-domain per-channel Q4.8 gain",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_data_i", raw_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_r_gain", 12),
            PortDesc("cfg_g_gain", 12),
            PortDesc("cfg_b_gain", 12),
            PortDesc("cfg_bayer", 2),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_data_o", raw_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("row", 1),
            StateDesc("col", 1),
        ],
        behavior=isp_wb_template(raw_width=raw_width),
    ))

    # =========================================================================
    # RGB Domain
    # =========================================================================

    # 10. ISPAWBStats (side-path)
    pes.append(ProcessingElement(
        name="ISPAWBStats",
        pe_type="isp_awb_stats",
        description="Auto white balance statistics: RGB channel sum accumulation",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_r_i", rgb_width),
            PortDesc("pix_g_i", rgb_width),
            PortDesc("pix_b_i", rgb_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("cfg_enable", 1),
        ],
        outputs=[
            PortDesc("stat_r_sum", 32),
            PortDesc("stat_g_sum", 32),
            PortDesc("stat_b_sum", 32),
            PortDesc("stat_pix_count", 32),
            PortDesc("stat_done", 1),
        ],
        state=[
            StateDesc("r_acc", 32),
            StateDesc("g_acc", 32),
            StateDesc("b_acc", 32),
            StateDesc("cnt", 32),
        ],
        behavior=isp_awb_stats_template(),
    ))

    # 11. ISPDemosaic
    pes.append(ProcessingElement(
        name="ISPDemosaic",
        pe_type="isp_demosaic",
        description="Malvar-He-Cutler 5x5 CFA interpolation: Bayer RAW to RGB",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_data_i", raw_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_bayer", 2),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_r_o", rgb_width),
            PortDesc("pix_g_o", rgb_width),
            PortDesc("pix_b_o", rgb_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("center_buf", raw_width),
            StateDesc("neighbors", 8 * raw_width),
            StateDesc("out_valid", 1),
            StateDesc("out_sof", 1),
            StateDesc("out_eol", 1),
            StateDesc("row", 1),
            StateDesc("col", 1),
        ],
        behavior=isp_demosaic_template(raw_width=raw_width, rgb_width=rgb_width),
    ))

    # 12. ISPCCM
    pes.append(ProcessingElement(
        name="ISPCCM",
        pe_type="isp_ccm",
        description="3x3 color correction matrix: Q4.8 signed MAC",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_r_i", rgb_width),
            PortDesc("pix_g_i", rgb_width),
            PortDesc("pix_b_i", rgb_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_c00", 12),
            PortDesc("cfg_c01", 12),
            PortDesc("cfg_c02", 12),
            PortDesc("cfg_c10", 12),
            PortDesc("cfg_c11", 12),
            PortDesc("cfg_c12", 12),
            PortDesc("cfg_c20", 12),
            PortDesc("cfg_c21", 12),
            PortDesc("cfg_c22", 12),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_r_o", rgb_width),
            PortDesc("pix_g_o", rgb_width),
            PortDesc("pix_b_o", rgb_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[],
        behavior=isp_ccm_template(rgb_width=rgb_width),
    ))

    # 13. ISPGamma
    pes.append(ProcessingElement(
        name="ISPGamma",
        pe_type="isp_gamma",
        description="Gamma correction: 4096-entry per-channel LUT",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_r_i", rgb_width),
            PortDesc("pix_g_i", rgb_width),
            PortDesc("pix_b_i", rgb_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_r_o", rgb_width),
            PortDesc("pix_g_o", rgb_width),
            PortDesc("pix_b_o", rgb_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("gamma_r_0", 12),
            StateDesc("gamma_g_0", 12),
            StateDesc("gamma_b_0", 12),
            # ... 4096 entries per channel
        ],
        behavior=isp_gamma_template(rgb_width=rgb_width),
    ))

    # =========================================================================
    # YUV Domain
    # =========================================================================

    # 14. ISPAEStats (side-path)
    pes.append(ProcessingElement(
        name="ISPAEStats",
        pe_type="isp_ae_stats",
        description="Auto exposure statistics: Y histogram with skewness",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_y_i", yuv_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_center_illum", 8),
        ],
        outputs=[
            PortDesc("stat_y_sum", 32),
            PortDesc("stat_y_sq_sum", 32),
            PortDesc("stat_y_cu_sum", 32),
            PortDesc("stat_pix_count", 32),
            PortDesc("stat_done", 1),
        ],
        state=[
            StateDesc("y_acc", 32),
            StateDesc("y_sq_acc", 32),
            StateDesc("y_cu_acc", 32),
            StateDesc("cnt", 32),
        ],
        behavior=isp_ae_stats_template(),
    ))

    # 15. ISPCSC
    pes.append(ProcessingElement(
        name="ISPCSC",
        pe_type="isp_csc",
        description="RGB to YCbCr color space conversion: BT.601/709",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_r_i", rgb_width),
            PortDesc("pix_g_i", rgb_width),
            PortDesc("pix_b_i", rgb_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_std", 1),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_y_o", yuv_width),
            PortDesc("pix_cb_o", yuv_width),
            PortDesc("pix_cr_o", yuv_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[],
        behavior=isp_csc_template(),
    ))

    # 16. ISPLDCI
    pes.append(ProcessingElement(
        name="ISPLDCI",
        pe_type="isp_ldci",
        description="CLAHE: contrast limited adaptive histogram equalization",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_y_i", yuv_width),
            PortDesc("pix_cb_i", yuv_width),
            PortDesc("pix_cr_i", yuv_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_clip_limit", 16),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_y_o", yuv_width),
            PortDesc("pix_cb_o", yuv_width),
            PortDesc("pix_cr_o", yuv_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("state", 2),
            StateDesc("frame_started", 1),
        ],
        behavior=isp_ldci_template(),
    ))

    # 17. ISPSharpen
    pes.append(ProcessingElement(
        name="ISPSharpen",
        pe_type="isp_sharpen",
        description="Unsharp masking: 3x3 Gaussian smoothing + detail enhancement",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_y_i", yuv_width),
            PortDesc("pix_cb_i", yuv_width),
            PortDesc("pix_cr_i", yuv_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_strength", 8),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_y_o", yuv_width),
            PortDesc("pix_cb_o", yuv_width),
            PortDesc("pix_cr_o", yuv_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("center_buf", yuv_width),
            StateDesc("neighbors", 8 * yuv_width),
            StateDesc("out_valid", 1),
            StateDesc("out_sof", 1),
            StateDesc("out_eol", 1),
            StateDesc("out_cb", yuv_width),
            StateDesc("out_cr", yuv_width),
        ],
        behavior=isp_sharpen_template(yuv_width=yuv_width),
    ))

    # 18. ISPNR2D
    pes.append(ProcessingElement(
        name="ISPNR2D",
        pe_type="isp_nr2d",
        description="2D noise reduction: Y-channel Gaussian smoothing blend",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_y_i", yuv_width),
            PortDesc("pix_cb_i", yuv_width),
            PortDesc("pix_cr_i", yuv_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_strength", 8),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_y_o", yuv_width),
            PortDesc("pix_cb_o", yuv_width),
            PortDesc("pix_cr_o", yuv_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("center_buf", yuv_width),
            StateDesc("neighbors", 8 * yuv_width),
            StateDesc("out_valid", 1),
            StateDesc("out_sof", 1),
            StateDesc("out_eol", 1),
            StateDesc("out_cb", yuv_width),
            StateDesc("out_cr", yuv_width),
        ],
        behavior=isp_nr2d_template(yuv_width=yuv_width),
    ))

    # 19. ISPScale
    pes.append(ProcessingElement(
        name="ISPScale",
        pe_type="isp_scale",
        description="Image scaling: nearest-neighbor downsampling",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_y_i", yuv_width),
            PortDesc("pix_cb_i", yuv_width),
            PortDesc("pix_cr_i", yuv_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_scale_x", 2),
            PortDesc("cfg_scale_y", 2),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_y_o", yuv_width),
            PortDesc("pix_cb_o", yuv_width),
            PortDesc("pix_cr_o", yuv_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("x_cnt", 16),
            StateDesc("y_cnt", 16),
        ],
        behavior=isp_scale_template(),
    ))

    # 20. ISPYUV
    pes.append(ProcessingElement(
        name="ISPYUV",
        pe_type="isp_yuv",
        description="YUV format conversion: 444/422/420 chroma subsampling",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_y_i", yuv_width),
            PortDesc("pix_cb_i", yuv_width),
            PortDesc("pix_cr_i", yuv_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("cfg_enable", 1),
            PortDesc("cfg_format", 2),
        ],
        outputs=[
            PortDesc("pix_valid_o", 1),
            PortDesc("pix_y_o", yuv_width),
            PortDesc("pix_cb_o", yuv_width),
            PortDesc("pix_cr_o", yuv_width),
            PortDesc("pix_sof_o", 1),
            PortDesc("pix_eol_o", 1),
        ],
        state=[
            StateDesc("x_cnt", 1),
            StateDesc("y_cnt", 1),
            StateDesc("cb_acc", yuv_width + 1),
            StateDesc("cr_acc", yuv_width + 1),
        ],
        behavior=isp_yuv_template(),
    ))

    # =========================================================================
    # IO / Control
    # =========================================================================

    # 21. ISPAXIStreamOut
    pes.append(ProcessingElement(
        name="ISPAXIStreamOut",
        pe_type="isp_axi_out",
        description="AXI-Stream master output: 24-bit YCbCr packed",
        inputs=[
            PortDesc("pix_valid_i", 1),
            PortDesc("pix_y_i", yuv_width),
            PortDesc("pix_cb_i", yuv_width),
            PortDesc("pix_cr_i", yuv_width),
            PortDesc("pix_sof_i", 1),
            PortDesc("pix_eol_i", 1),
            PortDesc("m_axis_tready", 1),
        ],
        outputs=[
            PortDesc("m_axis_tvalid", 1),
            PortDesc("m_axis_tdata", output_width),
            PortDesc("m_axis_tlast", 1),
            PortDesc("m_axis_tuser", 1),
        ],
        state=[
            StateDesc("out_reg", output_width),
            StateDesc("out_valid", 1),
            StateDesc("out_last", 1),
            StateDesc("out_user", 1),
        ],
        behavior=isp_axi_out_template(output_width=output_width),
    ))

    # 22. ISPAPBRegs
    pes.append(ProcessingElement(
        name="ISPAPBRegs",
        pe_type="isp_apb_regs",
        description="APB configuration register bank: 32x32-bit with field decode",
        inputs=[
            PortDesc("psel", 1),
            PortDesc("penable", 1),
            PortDesc("pwrite", 1),
            PortDesc("paddr", 8),
            PortDesc("pwdata", 32),
        ],
        outputs=[
            PortDesc("prdata", 32),
            PortDesc("pready", 1),
            PortDesc("pslverr", 1),
            PortDesc("cfg_crop_enable", 1),
            PortDesc("cfg_dpc_enable", 1),
            PortDesc("cfg_blc_enable", 1),
            PortDesc("cfg_dg_enable", 1),
            PortDesc("cfg_wb_enable", 1),
            PortDesc("cfg_demosaic_enable", 1),
            PortDesc("cfg_ccm_enable", 1),
            PortDesc("cfg_csc_enable", 1),
            PortDesc("cfg_gamma_enable", 1),
        ],
        state=[
            StateDesc("reg_0", 32),
            StateDesc("reg_1", 32),
            StateDesc("reg_2", 32),
            StateDesc("reg_3", 32),
            StateDesc("reg_4", 32),
            StateDesc("reg_5", 32),
            StateDesc("reg_6", 32),
            StateDesc("reg_7", 32),
            # ... 32 registers total
        ],
        behavior=isp_apb_regs_template(num_regs=num_regs),
    ))

    # =========================================================================
    # Interconnects: linear pipeline wiring
    # =========================================================================
    interconnects: List[InterconnectSpec] = [
        # AXI-In → Crop
        InterconnectSpec(
            src_pe="ISPAXIStreamIn", dst_pe="ISPCrop",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_data_o", raw_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # Crop → DPC
        InterconnectSpec(
            src_pe="ISPCrop", dst_pe="ISPDPC",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_data_o", raw_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # DPC → BLC
        InterconnectSpec(
            src_pe="ISPDPC", dst_pe="ISPBLC",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_data_o", raw_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # BLC → OECF
        InterconnectSpec(
            src_pe="ISPBLC", dst_pe="ISPOECF",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_data_o", raw_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # OECF → DG
        InterconnectSpec(
            src_pe="ISPOECF", dst_pe="ISPDG",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_data_o", raw_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # DG → LSC
        InterconnectSpec(
            src_pe="ISPDG", dst_pe="ISPLSC",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_data_o", raw_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # LSC → BNR
        InterconnectSpec(
            src_pe="ISPLSC", dst_pe="ISPBNR",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_data_o", raw_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # BNR → WB
        InterconnectSpec(
            src_pe="ISPBNR", dst_pe="ISPWB",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_data_o", raw_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # WB → Demosaic (Bayer→RGB boundary)
        InterconnectSpec(
            src_pe="ISPWB", dst_pe="ISPDemosaic",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_data_o", raw_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # Demosaic → CCM (RGB domain)
        InterconnectSpec(
            src_pe="ISPDemosaic", dst_pe="ISPCCM",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_r_o", rgb_width),
                     PortDesc("pix_g_o", rgb_width), PortDesc("pix_b_o", rgb_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # CCM → Gamma
        InterconnectSpec(
            src_pe="ISPCCM", dst_pe="ISPGamma",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_r_o", rgb_width),
                     PortDesc("pix_g_o", rgb_width), PortDesc("pix_b_o", rgb_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # Gamma → CSC (RGB→YUV boundary)
        InterconnectSpec(
            src_pe="ISPGamma", dst_pe="ISPCSC",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_r_o", rgb_width),
                     PortDesc("pix_g_o", rgb_width), PortDesc("pix_b_o", rgb_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # Demosaic → AWBStats (side-path)
        InterconnectSpec(
            src_pe="ISPDemosaic", dst_pe="ISPAWBStats",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_r_o", rgb_width),
                     PortDesc("pix_g_o", rgb_width), PortDesc("pix_b_o", rgb_width),
                     PortDesc("pix_sof_o", 1)],
        ),
        # CSC → LDCI (YUV domain)
        InterconnectSpec(
            src_pe="ISPCSC", dst_pe="ISPLDCI",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_y_o", yuv_width),
                     PortDesc("pix_cb_o", yuv_width), PortDesc("pix_cr_o", yuv_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # CSC → AEStats (side-path)
        InterconnectSpec(
            src_pe="ISPCSC", dst_pe="ISPAEStats",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_y_o", yuv_width),
                     PortDesc("pix_sof_o", 1)],
        ),
        # LDCI → Sharpen
        InterconnectSpec(
            src_pe="ISPLDCI", dst_pe="ISPSharpen",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_y_o", yuv_width),
                     PortDesc("pix_cb_o", yuv_width), PortDesc("pix_cr_o", yuv_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # Sharpen → NR2D
        InterconnectSpec(
            src_pe="ISPSharpen", dst_pe="ISPNR2D",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_y_o", yuv_width),
                     PortDesc("pix_cb_o", yuv_width), PortDesc("pix_cr_o", yuv_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # NR2D → Scale
        InterconnectSpec(
            src_pe="ISPNR2D", dst_pe="ISPScale",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_y_o", yuv_width),
                     PortDesc("pix_cb_o", yuv_width), PortDesc("pix_cr_o", yuv_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # Scale → YUV
        InterconnectSpec(
            src_pe="ISPScale", dst_pe="ISPYUV",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_y_o", yuv_width),
                     PortDesc("pix_cb_o", yuv_width), PortDesc("pix_cr_o", yuv_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # YUV → AXI-Out
        InterconnectSpec(
            src_pe="ISPYUV", dst_pe="ISPAXIStreamOut",
            signals=[PortDesc("pix_valid_o", 1), PortDesc("pix_y_o", yuv_width),
                     PortDesc("pix_cb_o", yuv_width), PortDesc("pix_cr_o", yuv_width),
                     PortDesc("pix_sof_o", 1), PortDesc("pix_eol_o", 1)],
        ),
        # APBRegs → all modules (enable fields)
        InterconnectSpec(
            src_pe="ISPAPBRegs", dst_pe="ISPCrop",
            signals=[PortDesc("cfg_crop_enable", 1)],
        ),
        InterconnectSpec(
            src_pe="ISPAPBRegs", dst_pe="ISPDPC",
            signals=[PortDesc("cfg_dpc_enable", 1)],
        ),
        InterconnectSpec(
            src_pe="ISPAPBRegs", dst_pe="ISPBLC",
            signals=[PortDesc("cfg_blc_enable", 1)],
        ),
        InterconnectSpec(
            src_pe="ISPAPBRegs", dst_pe="ISPDG",
            signals=[PortDesc("cfg_dg_enable", 1)],
        ),
        InterconnectSpec(
            src_pe="ISPAPBRegs", dst_pe="ISPWB",
            signals=[PortDesc("cfg_wb_enable", 1)],
        ),
        InterconnectSpec(
            src_pe="ISPAPBRegs", dst_pe="ISPDemosaic",
            signals=[PortDesc("cfg_demosaic_enable", 1)],
        ),
        InterconnectSpec(
            src_pe="ISPAPBRegs", dst_pe="ISPCCM",
            signals=[PortDesc("cfg_ccm_enable", 1)],
        ),
        InterconnectSpec(
            src_pe="ISPAPBRegs", dst_pe="ISPCSC",
            signals=[PortDesc("cfg_csc_enable", 1)],
        ),
        InterconnectSpec(
            src_pe="ISPAPBRegs", dst_pe="ISPGamma",
            signals=[PortDesc("cfg_gamma_enable", 1)],
        ),
    ]

    arch = ArchDefinition(
        name=design_name,
        isa="ISP",
        processing_elements=pes,
        interconnects=interconnects,
    )

    return arch
