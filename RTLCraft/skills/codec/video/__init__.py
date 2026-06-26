"""
skills.codec.video — xk265 H.265/HEVC Video Codec Skill

Architecture (38 modules across 9 pipeline stages):
  enc_ctrl      → Top-level encoder FSM (CTU sequencing)
  prei_top      → Pre-intra estimation (gradient + mode decision)
  posi_top      → Intra prediction search (SATD + partition decision)
  ime_top       → Integer motion estimation (multi-scale SAD)
  fme_top       → Fractional ME (1/4-pel interpolation)
  rec_top       → Reconstruction (intra + MC + TQ/iTQ + iDB)
  dbsao_top     → Deblocking filter + SAO
  cabac_top     → CABAC entropy coding (bina + bitpack)
  fetch_top     → Memory interface / pixel buffer manager

Submodules:
  IME: ime_ctrl, ime_addressing, ime_dat_array, ime_sad_array,
       ime_cost_store, ime_partition_decision, ime_partition_decision_engine,
       ime_mv_dump
  POSI: posi_ctrl, posi_transfer, posi_satd_cost_engine, posi_satd_cost,
        posi_rate_estimation, posi_partition_decision
  REC: tq_top, intra_top, mc_top, rec_buf_wrapper
  DBSAO: dbsao_controller, db_filter, db_bs
  CABAC: cabac_se_prepare, cabac_bina, cabac_bitpack
  FETCH: fetch_wrapper, fetch_cur_luma, fetch_ref_luma

Modules:
  - models.py: 38 golden reference behavioral models
  - dsl_modules.py: 38 DSL Module class definitions (ports, seq/comb logic, instantiate)
  - behaviors.py: 9 pipeline stage behavior templates
  - arch_templates.py: build_xk265_arch(), Xk265SuiteModel
  - skeleton_templates.py: PE type → implementation steps (12 PE types)
"""

# Register behaviors and skeleton steps at import time
import skills.codec.video.behaviors  # noqa: F401
import skills.codec.video.skeleton_templates  # noqa: F401

from skills.codec.video.models import (
    CTUState,
    H265EncoderModel,
    EncCtrlModel,
    # IME submodules
    ImeCtrlModel,
    ImeAddressingModel,
    ImeDatArrayModel,
    ImeSadArrayModel,
    ImeCostStoreModel,
    ImePartitionDecisionEngineModel,
    ImePartitionDecisionModel,
    ImeMvDumpModel,
    # POSI submodules
    PosiCtrlModel,
    PosiTransferModel,
    PosiSatdCostEngineModel,
    PosiRateEstimationModel,
    PosiSatdCostModel,
    PosiPartitionDecisionModel,
    # REC submodules
    TqTopModel,
    IntraTopModel,
    McTopModel,
    RecBufWrapperModel,
    # DBSAO submodules
    DbsaoControllerModel,
    DbFilterModel,
    DbBsModel,
    # CABAC submodules
    CabacSePrepareModel,
    CabacBinaModel,
    CabacBitpackModel,
    # FETCH submodules
    FetchWrapperModel,
    FetchCurLumaModel,
    FetchRefLumaModel,
    # Suite
    Xk265SuiteModel,
)
from skills.codec.video.arch_templates import (
    build_xk265_arch,
    Xk265SuiteModel,
    Codec_Model,
    CodecArchParams,
    CodecArchTemplate,
    BaselineCodecTemplate,
    HighPerfCodecTemplate,
    LowPowerCodecTemplate,
    get_template,
    list_templates,
    register_template,
)
from skills.codec.video.behaviors import (
    enc_ctrl_template,
    prei_template,
    posi_template,
    ime_template,
    fme_template,
    rec_template,
    dbsao_template,
    cabac_template,
    fetch_template,
)
from skills.codec.video.skeleton_templates import (
    ENC_CTRL_STEPS,
    PREI_TOP_STEPS,
    POSI_TOP_STEPS,
    IME_TOP_STEPS,
    FME_TOP_STEPS,
    REC_TOP_STEPS,
    DBSAO_TOP_STEPS,
    CABAC_TOP_STEPS,
    FETCH_TOP_STEPS,
    TQ_TOP_STEPS,
    INTRA_TOP_STEPS,
    MC_TOP_STEPS,
    register_xk265_skeleton_steps,
    register_codec_skeleton_steps,
)
from skills.codec.video.dsl_modules import (
    # Constants
    LCU_SIZE,
    LCU_SIZE_8,
    PIC_X_WIDTH,
    PIC_Y_WIDTH,
    PIC_WIDTH,
    PIC_HEIGHT,
    PIXEL_WIDTH,
    COEFF_WIDTH,
    IME_MV_WIDTH_X,
    IME_MV_WIDTH_Y,
    IME_MV_WIDTH,
    IME_C_MV_WIDTH,
    IME_PIXEL_WIDTH,
    IME_COST_WIDTH,
    CMD_NUM_WIDTH,
    CMD_DAT_WIDTH_ONE,
    CMD_DAT_WIDTH,
    POSI_COST_WIDTH,
    FMV_WIDTH,
    MVD_WIDTH,
    NUM_4X4,
    # Top-level hierarchy
    EncCore,
    Xk265Top,
    # 9 pipeline stages
    EncCtrl,
    PreiTop,
    PosiTop,
    ImeTop,
    FmeTop,
    RecTop,
    DbsaoTop,
    CabacTop,
    FetchTop,
    # IME submodules
    ImeCtrl,
    ImeAddressing,
    ImeDatArray,
    ImeSadArray,
    ImeCostStore,
    ImePartitionDecisionEngine,
    ImePartitionDecision,
    ImeMvDump,
    # POSI submodules
    PosiCtrl,
    PosiTransfer,
    PosiSatdCostEngine,
    PosiRateEstimation,
    PosiSatdCost,
    PosiPartitionDecision,
    # REC submodules
    TqTop,
    IntraTop,
    McTop,
    RecBufWrapper,
    # DBSAO submodules
    DbsaoController,
    DbFilter,
    DbBs,
    # CABAC submodules
    CabacSePrepare,
    CabacBina,
    CabacBitpack,
    # FETCH submodules
    FetchWrapper,
    FetchCurLuma,
    FetchRefLuma,
)

__all__ = [
    # Constants
    "LCU_SIZE", "LCU_SIZE_8",
    "PIC_X_WIDTH", "PIC_Y_WIDTH", "PIC_WIDTH", "PIC_HEIGHT",
    "PIXEL_WIDTH", "COEFF_WIDTH",
    "IME_MV_WIDTH_X", "IME_MV_WIDTH_Y", "IME_MV_WIDTH", "IME_C_MV_WIDTH",
    "IME_PIXEL_WIDTH", "IME_COST_WIDTH",
    "CMD_NUM_WIDTH", "CMD_DAT_WIDTH_ONE", "CMD_DAT_WIDTH",
    "POSI_COST_WIDTH", "FMV_WIDTH", "MVD_WIDTH", "NUM_4X4",
    # Top-level models
    "CTUState",
    "H265EncoderModel",
    "EncCtrlModel",
    # IME submodules
    "ImeCtrlModel",
    "ImeAddressingModel",
    "ImeDatArrayModel",
    "ImeSadArrayModel",
    "ImeCostStoreModel",
    "ImePartitionDecisionEngineModel",
    "ImePartitionDecisionModel",
    "ImeMvDumpModel",
    # POSI submodules
    "PosiCtrlModel",
    "PosiTransferModel",
    "PosiSatdCostEngineModel",
    "PosiRateEstimationModel",
    "PosiSatdCostModel",
    "PosiPartitionDecisionModel",
    # REC submodules
    "TqTopModel",
    "IntraTopModel",
    "McTopModel",
    "RecBufWrapperModel",
    # DBSAO submodules
    "DbsaoControllerModel",
    "DbFilterModel",
    "DbBsModel",
    # CABAC submodules
    "CabacSePrepareModel",
    "CabacBinaModel",
    "CabacBitpackModel",
    # FETCH submodules
    "FetchWrapperModel",
    "FetchCurLumaModel",
    "FetchRefLumaModel",
    # Suite
    "Xk265SuiteModel",
    # Architecture
    "build_xk265_arch",
    "Codec_Model",
    "CodecArchParams",
    "CodecArchTemplate",
    "BaselineCodecTemplate",
    "HighPerfCodecTemplate",
    "LowPowerCodecTemplate",
    "get_template",
    "list_templates",
    "register_template",
    # Behaviors
    "enc_ctrl_template",
    "prei_template",
    "posi_template",
    "ime_template",
    "fme_template",
    "rec_template",
    "dbsao_template",
    "cabac_template",
    "fetch_template",
    # Skeleton steps
    "ENC_CTRL_STEPS",
    "PREI_TOP_STEPS",
    "POSI_TOP_STEPS",
    "IME_TOP_STEPS",
    "FME_TOP_STEPS",
    "REC_TOP_STEPS",
    "DBSAO_TOP_STEPS",
    "CABAC_TOP_STEPS",
    "FETCH_TOP_STEPS",
    "TQ_TOP_STEPS",
    "INTRA_TOP_STEPS",
    "MC_TOP_STEPS",
    "register_xk265_skeleton_steps",
    "register_codec_skeleton_steps",
    # DSL module classes (38 RTL Module definitions)
    "EncCore", "Xk265Top",
    "EncCtrl", "PreiTop", "PosiTop", "ImeTop", "FmeTop",
    "RecTop", "DbsaoTop", "CabacTop", "FetchTop",
    "ImeCtrl", "ImeAddressing", "ImeDatArray", "ImeSadArray",
    "ImeCostStore", "ImePartitionDecisionEngine", "ImePartitionDecision", "ImeMvDump",
    "PosiCtrl", "PosiTransfer", "PosiSatdCostEngine", "PosiRateEstimation",
    "PosiSatdCost", "PosiPartitionDecision",
    "TqTop", "IntraTop", "McTop", "RecBufWrapper",
    "DbsaoController", "DbFilter", "DbBs",
    "CabacSePrepare", "CabacBina", "CabacBitpack",
    "FetchWrapper", "FetchCurLuma", "FetchRefLuma",
]
