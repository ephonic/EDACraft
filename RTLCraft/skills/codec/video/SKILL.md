# codec/video — xk265 H.265/HEVC Video Codec Design Skill

## Overview

Fudan University VIPcore xk265 H.265/HEVC CTU-level encoder.
Reference RTL: `ref_rtl/xk265`.

Architecture: 38 modules across 9 pipeline stages, CTU-level raster-scan encoding.

## Pipeline Stages (9)

| Stage | pe_type | Description |
|-------|---------|-------------|
| enc_ctrl | fsm_controller | Top-level FSM: CTU sequencing, 10-state pipeline control |
| prei_top | prei_processor | Pre-intra: Sobel gradient (GxGy), mode pre-screening, rate control |
| posi_top | posi_processor | Intra search: 35-mode SATD cost, quad-tree partition decision |
| ime_top | ime_processor | Integer ME: multi-scale SAD (4x4→32x32), search pattern traversal, MV dump |
| fme_top | fme_processor | Fractional ME: 1/4-pel interpolation, refinement |
| rec_top | rec_processor | Reconstruction: intra prediction, motion compensation, TQ/iTQ |
| dbsao_top | dbsao_processor | Deblocking filter (BS computation, strong/weak filter) + SAO (EO/BO) |
| cabac_top | cabac_processor | CABAC entropy coding: syntax element prep, binarization, bitpack |
| fetch_top | fetch_processor | Memory interface: current/ref luma buffers, external AXI/DDR |

## All Modules (38)

### Top-Level Control
| Module | Submodules | Description |
|--------|------------|-------------|
| enc_ctrl | — | CTU raster-scan FSM, per-stage start/done sequencing |

### Pre-Intra Estimation
| Module | Submodules | Description |
|--------|------------|-------------|
| prei_top | — | Gradient engine + mode decision + rate control |

### Intra Prediction Search
| Module | Submodules | Description |
|--------|------------|-------------|
| posi_top | posi_ctrl, posi_transfer, posi_satd_cost_engine, posi_satd_cost, posi_rate_estimation, posi_partition_decision | SATD-based 35-mode intra search with hierarchical partition decision |
| posi_ctrl | — | 9-state FSM: TRA_PRE → TRA_POS → SIZE_4x4/8x8/16x16/32x32 → DECISION → DONE |
| posi_transfer | — | Original pixel read, row/col/frame RAM write |
| posi_satd_cost_engine | — | 8-point 1-D Hadamard butterfly transform |
| posi_satd_cost | — | 2-D Hadamard + rate cost, 10-stage pipeline |
| posi_rate_estimation | — | Lambda-based bit estimation from QP |
| posi_partition_decision | — | Hierarchical RDO quad-tree, per-size best cost tracking |

### Integer Motion Estimation
| Module | Submodules | Description |
|--------|------------|-------------|
| ime_top | ime_ctrl, ime_addressing, ime_dat_array (×2), ime_sad_array, ime_cost_store, ime_partition_decision_engine, ime_partition_decision, ime_mv_dump | Multi-scale SAD search with partition-aware MV output |
| ime_ctrl | — | 5-state FSM: IDLE → ADR → DEC → DMP → DONE |
| ime_addressing | — | Search pattern traversal (center, length, slope, downsample, feedback) |
| ime_dat_array | — | 32×32 pixel buffer, horizontal/vertical shift register |
| ime_sad_array | — | Hierarchical SAD: 64×4x4 + 16×8x8 + 4×16x16 + 1×32x32 |
| ime_cost_store | — | Best SAD+MVD cost per block size (8x8/16x16/32x32/64x64) |
| ime_partition_decision_engine | — | Combinational: 1Nx1N vs 1Nx2N vs 2Nx1N vs 2Nx2N |
| ime_partition_decision | — | 21-step iterative CTU quad-tree partition |
| ime_mv_dump | — | Serial MV output for all 64 8×8 blocks |

### Fractional Motion Estimation
| Module | Submodules | Description |
|--------|------------|-------------|
| fme_top | — | 1/4-pel interpolation + refinement (3-state FSM) |

### Reconstruction
| Module | Submodules | Description |
|--------|------------|-------------|
| rec_top | tq_top, intra_top, mc_top, rec_buf_wrapper | Reconstruction loop: intra/MC/TQ with CBF management |
| tq_top | — | DCT/DST transform + quantization + inverse (32-cycle pipeline) |
| intra_top | — | Intra prediction controller (256-cycle per-CTU, 35 modes) |
| mc_top | — | Motion compensation controller (64-cycle, MV read + ref fetch + FME write) |
| rec_buf_wrapper | — | Central memory hub: CBF Y/U/V flag management |

### Deblocking + SAO
| Module | Submodules | Description |
|--------|------------|-------------|
| dbsao_top | dbsao_controller, db_filter, db_bs | Deblocking filter + Sample Adaptive Offset |
| dbsao_controller | — | 7-state FSM: LOAD → DBY → DBU → DBV → SAO → OUT |
| db_bs | — | Boundary strength: TU/PU edge, QP, CBF flags |
| db_filter | — | HEVC deblocking on 4×4 edge (strong/weak filter selection) |

### CABAC Entropy Coding
| Module | Submodules | Description |
|--------|------------|-------------|
| cabac_top | cabac_se_prepare, cabac_bina, cabac_bitpack | Context-adaptive binary arithmetic coding |
| cabac_se_prepare | — | CU quad-tree traversal, syntax element emission, LCU done |
| cabac_bina | — | Syntax element binarization (TR, EGk, FL) |
| cabac_bitpack | — | Bin-to-byte packing, emulation prevention, 128-bit buffer |

### Memory Fetch
| Module | Submodules | Description |
|--------|------------|-------------|
| fetch_top | fetch_wrapper, fetch_cur_luma, fetch_ref_luma | Memory interface for current/ref luma + DB writeback |
| fetch_wrapper | — | Top-level arbiter/scheduler (256-cycle access sequence) |
| fetch_cur_luma | — | 4-bank rotating current luma buffer |
| fetch_ref_luma | — | 1024-entry reference luma buffer |

## Files

| File | Description |
|------|-------------|
| `models.py` | 38 cycle-accurate Python simulators (CTUState, H265EncoderModel, EncCtrlModel, 8 IME models, 6 POSI models, 4 REC models, 3 DBSAO models, 3 CABAC models, 3 FETCH models, Xk265SuiteModel) |
| `dsl_modules.py` | 38 DSL Module class definitions (Input/Output/Reg/Wire ports, seq/comb logic, instantiate calls) extracted from design_xk265.py |
| `behaviors.py` | 9 pipeline stage behavior templates (CycleContext pattern, TemplateRegistry) |
| `arch_templates.py` | CodecArchParams, CodecPeCatalog (9 PE builders), 3 concrete templates (Baseline/HighPerf/LowPower), build_xk265_arch() |
| `skeleton_templates.py` | 12 PE type → implementation step lists (ENC_CTRL through MC_TOP) |

## Quick Start

```python
from skills.codec.video.arch_templates import build_xk265_arch

arch = build_xk265_arch(variant="baseline")
```

```python
from skills.codec.video.models import Xk265SuiteModel

suite = Xk265SuiteModel(lcu_size=64, pic_width=1920, pic_height=1080)
result = suite.run(num_cycles=10000)
print(result)
```

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| LCU_SIZE | 64 | Largest coding unit (64×64 pixels) |
| CU_DEPTH | 3 | Quad-tree depth (64→32→16→8) |
| PIXEL_WIDTH | 8 | Bits per pixel |
| COEFF_WIDTH | 16 | Transform coefficient width |
| IME_MV_WIDTH | 13 | Motion vector width (7b X + 6b Y) |
| IME_COST_WIDTH | 28 | IME cost (SAD + λ×MVD) width |
| POSI_COST_WIDTH | 20 | Intra SATD cost width |
| FME_COST_WIDTH | 20 | Fractional ME cost width |
| FMV_WIDTH | 10 | FME MV width |
| MVD_WIDTH | 11 | MVD width |
| NUM_4X4 | 256 | 4×4 blocks per 64×64 LCU |
