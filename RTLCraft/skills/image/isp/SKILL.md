# ISP (Image Signal Processor) Skill

Professional-grade ISP pipeline based on Infinite-ISP v1.1 reference model.
Pixel-rate processing from 12-bit Bayer RAW to 24-bit YCbCr output.

## Architecture

The ISP is organized into three processing domains:

### Bayer Domain (RAW pixel processing)
```
AXI-In → Crop → DPC(5×5 Dynamic) → BLC → OECF → DG → LSC → BNR(JBF) → WB
```

### RGB Domain (after demosaicing)
```
Demosaic(Malvar 5×5) → CCM(3×3 MAC) → Gamma(4096 LUT)
```

### YUV Domain (after color space conversion)
```
CSC(BT.601/709) → LDCI(CLAHE) → Sharpen(UM) → NR2D → Scale → YUV → AXI-Out
```

### Control & Statistics (side paths)
```
APB Regs (32×32-bit config) → all modules
AWB Stats (RGB accumulation) ← Demosaic output
AE Stats (Y histogram + skewness) ← CSC output
```

## Module PE Mapping

| PE Type | Submodule | Behavior Template | Window | Key Algorithm |
|---------|-----------|-------------------|--------|---------------|
| `isp_axi_in` | ISPAXIStreamIn | isp_axi_in_template | N/A | AXI-Stream handshake, 2-stage FIFO |
| `isp_crop` | ISPCrop | isp_crop_template | N/A | x/y counter region gating |
| `isp_dpc` | ISPDPC | isp_dpc_template | 5×5 | Dynamic DPC, 8-dir gradient, min-grad mean |
| `isp_blc` | ISPBLC | isp_blc_template | N/A | Per-channel Bayer offset subtract |
| `isp_oecf` | ISPOECF | isp_oecf_template | N/A | Per-channel LUT (256 entries) |
| `isp_dg` | ISPDG | isp_dg_template | N/A | Q4.8 fixed-point gain, saturation clip |
| `isp_lsc` | ISPLSC | isp_lsc_template | N/A | Radial gain model, per-channel Bayer |
| `isp_bnr` | ISPBNR | isp_bnr_template | 5×5 | Joint Bilateral Filter, Green Guiding |
| `isp_wb` | ISPWB | isp_wb_template | N/A | Bayer-aware R/G/B gain (Q4.8) |
| `isp_awb_stats` | ISPAWBStats | isp_awb_stats_template | N/A | RGB channel sum accumulation |
| `isp_demosaic` | ISPDemosaic | isp_demosaic_template | 5×5 | Malvar-He-Cutler interpolation |
| `isp_ccm` | ISPCCM | isp_ccm_template | N/A | 3×3 matrix MAC (Q4.8 signed) |
| `isp_gamma` | ISPGamma | isp_gamma_template | N/A | 4096-entry per-channel LUT |
| `isp_ae_stats` | ISPAEStats | isp_ae_stats_template | N/A | Y sum/sq/cu for skewness |
| `isp_csc` | ISPCSC | isp_csc_template | N/A | RGB→YCbCr (BT.601/709) |
| `isp_ldci` | ISPLDCI | isp_ldci_template | 8×8 tiles | CLAHE with ping-pong LUTs |
| `isp_sharpen` | ISPSharpen | isp_sharpen_template | 3×3 | Unsharp masking, Gaussian blur |
| `isp_nr2d` | ISPNR2D | isp_nr2d_template | 3×3 | Y-channel Gaussian smoothing blend |
| `isp_scale` | ISPScale | isp_scale_template | N/A | Nearest-neighbor downsampling |
| `isp_yuv` | ISPYUV | isp_yuv_template | N/A | 444→422/420 chroma subsampling |
| `isp_axi_out` | ISPAXIStreamOut | isp_axi_out_template | N/A | AXI-Stream master, 24-bit output |
| `isp_apb_regs` | ISPAPBRegs | isp_apb_regs_template | N/A | 32×32-bit APB register bank |

## Key Design Patterns

1. **Line-buffer window generators**: DPC, BNR, Demosaic use 4 line buffers
   for 5×5 spatial windows. Sharpen, NR2D use 2 line buffers for 3×3.
2. **Bayer pattern awareness**: BLC, LSC, WB, Demosaic all track row/col parity
   to identify R/G/B positions in RGGB/BGGR/GRBG/GBRG patterns.
3. **Fixed-point arithmetic**: Gains use Q4.8 (12-bit), CCM coefficients use
   Q4.8 signed, LDCI clip limit uses 16-bit.
4. **LUT-based nonlinearities**: OECF (256-entry), Gamma (4096-entry),
   LDCI (64 tiles × 256 bins, ping-pong buffered), BNR range LUT (256 exp).
5. **Stream protocol**: All modules use `pix_valid/pix_sof/pix_eol` handshake.
   SOF resets counters, EOL wraps x counter and advances y counter.
6. **3A statistics**: AWB stats (RGB sums) and AE stats (Y histogram + skewness)
   run as side-path accumulators, resetting on SOF.

## Reference

Based on Infinite-ISP v1.1 (ref_rtl/ISP/) by 10xEngineers Pvt Ltd.
See `design_isp.py` for the full RTLGEN DSL implementation.

## Usage

```python
from skills.image.behaviors import (
    isp_crop_template, isp_dpc_template, isp_blc_template,
    isp_demosaic_template, isp_ccm_template, isp_csc_template,
    isp_ldci_template, isp_sharpen_template,
)
from skills.image.models import ISPModel
from skills.image.arch_templates import build_isp_arch
```
