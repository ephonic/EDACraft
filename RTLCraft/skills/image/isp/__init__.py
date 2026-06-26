"""
skills.image — ISP (Image Signal Processor) Skill

Domain-specific skill for image signal processing pipelines.
Based on Infinite-ISP v1.1 reference model.

Pipeline: Bayer (RAW) → RGB → YUV
  Bayer: Crop → DPC → BLC → OECF → DG → LSC → BNR → WB
  RGB:   Demosaic → CCM → Gamma
  YUV:   CSC → LDCI → Sharpen → NR2D → Scale → YUV
  Stats: AWB (RGB sums), AE (Y histogram + skewness)
  Config: APB register bank (32×32-bit)

Modules:
  - behaviors.py: 22 cycle-accurate behavior templates
  - models.py: ISPModel golden-reference simulator
  - arch_templates.py: build_isp_arch() for ProcessingElement + InterconnectSpec
  - skeleton_templates.py: DSL skeleton generation steps for 22 PE types
"""

# Register behaviors and skeleton steps at import time
import skills.image.isp.behaviors  # noqa: F401
import skills.image.isp.skeleton_templates  # noqa: F401

from skills.image.isp.models import ISPModel
from skills.image.isp.arch_templates import ISP_Model, build_isp_arch
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

from skills.image.isp.dsl_modules import (
    ISPAXIStreamIn,
    ISPCrop,
    ISPDPC,
    ISPBLC,
    ISPOECF,
    ISPDG,
    ISPLSC,
    ISPBNR,
    ISPWB,
    ISPAWBStats,
    ISPDemosaic,
    ISPCCM,
    ISPGamma,
    ISPAEStats,
    ISPCSC,
    ISPLDCI,
    ISPSharpen,
    ISPNR2D,
    ISPScale,
    ISPYUV,
    ISPAXIStreamOut,
    ISPAPBRegs,
    ISPController,
)

__all__ = [
    "ISPAXIStreamIn", "ISPCrop", "ISPDPC", "ISPBLC", "ISPOECF", "ISPDG", "ISPLSC", "ISPBNR", "ISPWB", "ISPAWBStats", "ISPDemosaic", "ISPCCM", "ISPGamma", "ISPAEStats", "ISPCSC", "ISPLDCI", "ISPSharpen", "ISPNR2D", "ISPScale", "ISPYUV", "ISPAXIStreamOut", "ISPAPBRegs", "ISPController",
    "ISPModel",
    "ISP_Model",
    "build_isp_arch",
    "isp_axi_in_template",
    "isp_crop_template",
    "isp_dpc_template",
    "isp_blc_template",
    "isp_oecf_template",
    "isp_dg_template",
    "isp_lsc_template",
    "isp_bnr_template",
    "isp_wb_template",
    "isp_awb_stats_template",
    "isp_demosaic_template",
    "isp_ccm_template",
    "isp_gamma_template",
    "isp_ae_stats_template",
    "isp_csc_template",
    "isp_ldci_template",
    "isp_sharpen_template",
    "isp_nr2d_template",
    "isp_scale_template",
    "isp_yuv_template",
    "isp_axi_out_template",
    "isp_apb_regs_template",
]
