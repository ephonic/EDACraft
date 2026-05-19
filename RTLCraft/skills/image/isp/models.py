"""
skills.image.models — ISP Behavioral Models

Cycle-accurate behavioral models for ISP pipeline stages.
Used for golden-reference simulation and verification comparison.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from rtlgen.arch_def import CycleContext, ModelProvider


class ISPModel(ModelProvider):
    """Golden-reference behavioral model for the full ISP pipeline.

    Simulates the complete Bayer→RGB→YUV processing chain:
      Bayer: Crop → DPC → BLC → OECF → DG → LSC → BNR → WB
      RGB:   Demosaic → CCM → Gamma
      YUV:   CSC → LDCI → Sharpen → NR2D → Scale → YUV

    Stats side-paths: AWBStats (RGB sums), AEStats (Y histogram + skewness)
    """

    name = "isp_model"
    description = "ISP pipeline golden-reference model (Bayer→RGB→YUV)"

    def create_behavior(
        self,
        bayer_pattern: int = 0,       # 0=RGGB, 1=BGGR, 2=GRBG, 3=GBRG
        raw_width: int = 12,
        rgb_width: int = 12,
        yuv_width: int = 8,
        csc_std: int = 1,              # 0=BT.709, 1=BT.601
        yuv_format: int = 0,           # 0=444, 1=422, 2=420
        scale_x: int = 0,
        scale_y: int = 0,
        **kwargs,
    ):
        """Create a full-pipeline ISP behavioral model.

        Processes one pixel per cycle through the complete chain.
        Statistics (AWB/AE) are accumulated as side-paths.
        """

        def behavior(ctx: CycleContext):
            # Top-level inputs
            pix_valid = ctx.get_input("pix_valid_i", 0)
            pix_data = ctx.get_input("pix_data_i", 0)
            pix_sof = ctx.get_input("pix_sof_i", 0)
            pix_eol = ctx.get_input("pix_eol_i", 0)

            # Frame tracking
            row = ctx.get_state("frame_row", 0)
            col = ctx.get_state("frame_col", 0)

            if pix_sof:
                row = 0
                col = 0
            elif pix_valid and pix_eol:
                row = 1 - row
                col = 0
            elif pix_valid:
                col = 1 - col

            # =========================================================
            # Bayer Domain Processing
            # =========================================================

            # --- Crop (passthrough in behavioral model) ---
            crop_valid = pix_valid
            crop_data = pix_data

            # --- DPC (simplified dead pixel check) ---
            dpc_center = ctx.get_state("dpc_center", 0)
            dpc_valid = ctx.get_state("dpc_valid", 0)
            if pix_valid:
                if dpc_valid:
                    dpc_result = dpc_center  # simplified: no correction
                else:
                    dpc_result = pix_data
                    ctx.set_state("dpc_valid", 1)
                ctx.set_state("dpc_center", pix_data)
            else:
                dpc_result = dpc_center
            dpc_data = dpc_result
            dpc_valid_out = dpc_valid

            # --- BLC (black level correction) ---
            blc_enable = ctx.get_input("cfg_blc_enable", 1)
            blc_r_off = ctx.get_input("cfg_blc_r_offset", 0)
            blc_gr_off = ctx.get_input("cfg_blc_gr_offset", 0)
            blc_gb_off = ctx.get_input("cfg_blc_gb_offset", 0)
            blc_b_off = ctx.get_input("cfg_blc_b_offset", 0)

            pixel_max = (1 << raw_width) - 1
            if bayer_pattern == 0:  # RGGB
                blc_off = blc_r_off if (row == 0 and col == 0) else \
                          blc_gr_off if (row == 0) else \
                          blc_gb_off if (col == 0) else blc_b_off
            else:
                blc_off = 0

            blc_sub = max(0, dpc_data - blc_off) if blc_enable else dpc_data
            blc_data = min(blc_sub, pixel_max)

            # --- OECF (LUT passthrough) ---
            oecf_enable = ctx.get_input("cfg_oecf_enable", 1)
            oecf_idx = blc_data >> (raw_width - 8)
            oecf_val = ctx.get_state(f"oecf_lut_{oecf_idx}", oecf_idx)
            oecf_data = oecf_val if oecf_enable else blc_data

            # --- DG (digital gain) ---
            dg_enable = ctx.get_input("cfg_dg_enable", 1)
            dg_gain = ctx.get_input("cfg_dg_gain", 256)
            if dg_enable:
                dg_prod = oecf_data * dg_gain
                dg_data = min(dg_prod >> 8, pixel_max)
            else:
                dg_data = oecf_data

            # --- LSC (lens shading correction) ---
            lsc_enable = ctx.get_input("cfg_lsc_enable", 1)
            lsc_gain_r = ctx.get_input("cfg_lsc_gain_r", 16)
            lsc_gain_gr = ctx.get_input("cfg_lsc_gain_gr", 16)
            lsc_gain_gb = ctx.get_input("cfg_lsc_gain_gb", 16)
            lsc_gain_b = ctx.get_input("cfg_lsc_gain_b", 16)

            if bayer_pattern == 0:
                lsc_gain = lsc_gain_r if (row == 0 and col == 0) else \
                           lsc_gain_gr if (row == 0) else \
                           lsc_gain_gb if (col == 0) else lsc_gain_b
            else:
                lsc_gain = 16

            if lsc_enable:
                lsc_prod = dg_data * lsc_gain
                lsc_data = min(lsc_prod >> 4, pixel_max)
            else:
                lsc_data = dg_data

            # --- BNR (simplified passthrough) ---
            bnr_enable = ctx.get_input("cfg_bnr_enable", 1)
            bnr_data = lsc_data  # simplified: full BNR needs 5x5 window

            # --- WB (white balance) ---
            wb_enable = ctx.get_input("cfg_wb_enable", 1)
            wb_r_gain = ctx.get_input("cfg_wb_r_gain", 256)
            wb_g_gain = ctx.get_input("cfg_wb_g_gain", 256)
            wb_b_gain = ctx.get_input("cfg_wb_b_gain", 256)

            if bayer_pattern == 0:
                is_r = (row == 0 and col == 0)
                is_b = (row == 1 and col == 1)
            else:
                is_r = False
                is_b = False

            wb_gain = wb_r_gain if is_r else (wb_b_gain if is_b else wb_g_gain)
            if wb_enable:
                wb_prod = bnr_data * wb_gain
                wb_data = min(wb_prod >> 8, pixel_max)
            else:
                wb_data = bnr_data

            # =========================================================
            # RGB Domain (after demosaic)
            # =========================================================

            demosaic_enable = ctx.get_input("cfg_demosaic_enable", 1)
            if bayer_pattern == 0:
                is_r = (row == 0 and col == 0)
                is_b = (row == 1 and col == 1)
            else:
                is_r = False
                is_b = False

            if demosaic_enable:
                if is_r:
                    pix_r = wb_data
                    pix_g = ctx.get_state("dem_g_interp", wb_data)
                    pix_b = ctx.get_state("dem_b_interp", wb_data)
                elif is_b:
                    pix_r = ctx.get_state("dem_r_interp", wb_data)
                    pix_g = ctx.get_state("dem_g_interp", wb_data)
                    pix_b = wb_data
                else:
                    pix_r = ctx.get_state("dem_r_interp", wb_data)
                    pix_g = wb_data
                    pix_b = ctx.get_state("dem_b_interp", wb_data)

                ctx.set_state("dem_r_interp", wb_data)
                ctx.set_state("dem_g_interp", wb_data)
                ctx.set_state("dem_b_interp", wb_data)
            else:
                pix_r = wb_data
                pix_g = wb_data
                pix_b = wb_data

            # --- CCM (color correction matrix) ---
            ccm_enable = ctx.get_input("cfg_ccm_enable", 1)
            rgb_max = (1 << rgb_width) - 1

            def smul(pix, coeff):
                neg = coeff & 0x800
                coeff_abs = ((~coeff + 1) & 0xFFF) if neg else coeff
                prod = pix * coeff_abs
                return (-prod) if neg else prod

            c00 = ctx.get_input("cfg_ccm_c00", 256)
            c01 = ctx.get_input("cfg_ccm_c01", 0)
            c02 = ctx.get_input("cfg_ccm_c02", 0)
            c10 = ctx.get_input("cfg_ccm_c10", 0)
            c11 = ctx.get_input("cfg_ccm_c11", 256)
            c12 = ctx.get_input("cfg_ccm_c12", 0)
            c20 = ctx.get_input("cfg_ccm_c20", 0)
            c21 = ctx.get_input("cfg_ccm_c21", 0)
            c22 = ctx.get_input("cfg_ccm_c22", 256)

            if ccm_enable:
                r_acc = smul(pix_r, c00) + smul(pix_g, c01) + smul(pix_b, c02)
                g_acc = smul(pix_r, c10) + smul(pix_g, c11) + smul(pix_b, c12)
                b_acc = smul(pix_r, c20) + smul(pix_g, c21) + smul(pix_b, c22)
                pix_r = min(max(r_acc >> 8, 0), rgb_max)
                pix_g = min(max(g_acc >> 8, 0), rgb_max)
                pix_b = min(max(b_acc >> 8, 0), rgb_max)

            # --- Gamma (LUT passthrough) ---
            gamma_enable = ctx.get_input("cfg_gamma_enable", 1)
            if gamma_enable:
                pix_r = ctx.get_state(f"gamma_r_{pix_r}", pix_r)
                pix_g = ctx.get_state(f"gamma_g_{pix_g}", pix_g)
                pix_b = ctx.get_state(f"gamma_b_{pix_b}", pix_b)

            # =========================================================
            # AWB Stats (side-path)
            # =========================================================
            awb_enable = ctx.get_input("cfg_awb_enable", 1)
            awb_r_acc = ctx.get_state("awb_r_acc", 0)
            awb_g_acc = ctx.get_state("awb_g_acc", 0)
            awb_b_acc = ctx.get_state("awb_b_acc", 0)
            awb_cnt = ctx.get_state("awb_cnt", 0)

            if pix_sof:
                awb_r_acc = 0
                awb_g_acc = 0
                awb_b_acc = 0
                awb_cnt = 0

            if pix_valid and awb_enable:
                awb_r_acc += pix_r
                awb_g_acc += pix_g
                awb_b_acc += pix_b
                awb_cnt += 1

            ctx.set_output("awb_r_sum", awb_r_acc)
            ctx.set_output("awb_g_sum", awb_g_acc)
            ctx.set_output("awb_b_sum", awb_b_acc)
            ctx.set_output("awb_pix_count", awb_cnt)

            ctx.set_state("awb_r_acc", awb_r_acc)
            ctx.set_state("awb_g_acc", awb_g_acc)
            ctx.set_state("awb_b_acc", awb_b_acc)
            ctx.set_state("awb_cnt", awb_cnt)

            # =========================================================
            # YUV Domain (after CSC)
            # =========================================================

            csc_enable = ctx.get_input("cfg_csc_enable", 1)
            bt709 = (csc_std == 0)

            if csc_enable:
                if bt709:
                    y_acc = 47 * pix_r + 157 * pix_g + 16 * pix_b
                    cb_acc = -26 * pix_r - 86 * pix_g + 112 * pix_b
                    cr_acc = 112 * pix_r - 102 * pix_g - 10 * pix_b
                else:
                    y_acc = 77 * pix_r + 150 * pix_g + 29 * pix_b
                    cb_acc = -43 * pix_r - 85 * pix_g + 128 * pix_b
                    cr_acc = 128 * pix_r - 107 * pix_g - 21 * pix_b

                pix_y = min(max(y_acc >> 8, 0), 255)
                pix_cb = min(max((cb_acc >> 8) + 128, 0), 255)
                pix_cr = min(max((cr_acc >> 8) + 128, 0), 255)
            else:
                pix_y = pix_r
                pix_cb = pix_g
                pix_cr = pix_b

            # --- LDCI (CLAHE, simplified passthrough) ---
            ldci_enable = ctx.get_input("cfg_ldci_enable", 1)
            # Full CLAHE needs tile histogram; simplified: passthrough

            # --- Sharpen (unsharp masking) ---
            sharpen_enable = ctx.get_input("cfg_sharpen_enable", 1)
            sharpen_strength = ctx.get_input("cfg_sharpen_strength", 16)
            sharpen_center = ctx.get_state("sharpen_center", pix_y)

            if sharpen_enable:
                neighbors = ctx.get_state("sharpen_neighbors", [sharpen_center] * 8)
                corners = sum(neighbors[i] for i in [0, 2, 4, 6])
                edges = sum(neighbors[i] for i in [1, 3, 5, 7])
                smoothed = (corners + (edges << 1) + (sharpen_center << 2)) >> 4
                detail = sharpen_center - smoothed
                scaled = (detail * sharpen_strength) >> 4
                pix_y = min(max(sharpen_center + scaled, 0), 255)
                ctx.set_state("sharpen_neighbors", [sharpen_center] + neighbors[:7])

            ctx.set_state("sharpen_center", pix_y)

            # --- NR2D (2D noise reduction) ---
            nr2d_enable = ctx.get_input("cfg_nr2d_enable", 1)
            nr2d_strength = ctx.get_input("cfg_nr2d_strength", 4)

            if nr2d_enable:
                nr_center = ctx.get_state("nr2d_center", pix_y)
                nr_neighbors = ctx.get_state("nr2d_neighbors", [nr_center] * 8)
                smooth = (nr_center + sum(nr_neighbors[:8])) >> 3
                pix_y = min(max((nr_center * (16 - nr2d_strength) + smooth * nr2d_strength) >> 4, 0), 255)
                ctx.set_state("nr2d_center", pix_y)
                ctx.set_state("nr2d_neighbors", [nr_center] + nr_neighbors[:7])

            # --- AE Stats (side-path) ---
            ae_enable = ctx.get_input("cfg_ae_enable", 1)
            ae_center = ctx.get_input("cfg_ae_center_illum", 128)
            ae_y_acc = ctx.get_state("ae_y_acc", 0)
            ae_y_sq = ctx.get_state("ae_y_sq_acc", 0)
            ae_y_cu = ctx.get_state("ae_y_cu_acc", 0)
            ae_cnt = ctx.get_state("ae_cnt", 0)

            if pix_sof:
                ae_y_acc = 0
                ae_y_sq = 0
                ae_y_cu = 0
                ae_cnt = 0

            if pix_valid and ae_enable:
                y_c = abs(pix_y - ae_center)
                ae_y_acc += pix_y
                ae_y_sq += y_c * y_c
                sign = 1 if pix_y > ae_center else -1
                ae_y_cu += sign * y_c * y_c * y_c
                ae_cnt += 1

            ctx.set_output("ae_y_sum", ae_y_acc)
            ctx.set_output("ae_y_sq_sum", ae_y_sq)
            ctx.set_output("ae_y_cu_sum", ae_y_cu)
            ctx.set_output("ae_pix_count", ae_cnt)

            ctx.set_state("ae_y_acc", ae_y_acc)
            ctx.set_state("ae_y_sq_acc", ae_y_sq)
            ctx.set_state("ae_y_cu_acc", ae_y_cu)
            ctx.set_state("ae_cnt", ae_cnt)

            # --- Scale ---
            scale_enable = ctx.get_input("cfg_scale_enable", 1)
            sc_x = ctx.get_input("cfg_scale_x", scale_x)
            sc_y = ctx.get_input("cfg_scale_y", scale_y)
            sc_x_cnt = ctx.get_state("scale_x_cnt", 0)
            sc_y_cnt = ctx.get_state("scale_y_cnt", 0)

            if pix_sof:
                sc_y_cnt = 0
            elif pix_valid and pix_eol:
                sc_x_cnt = 0
                sc_y_cnt += 1
            elif pix_valid:
                sc_x_cnt += 1

            out_x = True if sc_x == 0 else (sc_x_cnt % 2 == 0) if sc_x == 1 else (sc_x_cnt % 4 == 0)
            out_y = True if sc_y == 0 else (sc_y_cnt % 2 == 0) if sc_y == 1 else (sc_y_cnt % 4 == 0)

            if scale_enable:
                emit = pix_valid and out_x and out_y
            else:
                emit = pix_valid

            ctx.set_state("scale_x_cnt", sc_x_cnt)
            ctx.set_state("scale_y_cnt", sc_y_cnt)

            # --- YUV format ---
            yuv_fmt = ctx.get_input("cfg_yuv_format", yuv_format)
            x_cnt = ctx.get_state("yuv_x_cnt", 0)

            if yuv_fmt == 0:  # 444
                out_y_val = pix_y
                out_cb = pix_cb
                out_cr = pix_cr
            else:  # 422/420: chroma averaging
                cb_acc = ctx.get_state("yuv_cb_acc", 0)
                cr_acc = ctx.get_state("yuv_cr_acc", 0)
                if x_cnt == 0:
                    out_y_val = pix_y
                    out_cb = cb_acc >> 1
                    out_cr = cr_acc >> 1
                    ctx.set_state("yuv_cb_acc", pix_cb)
                    ctx.set_state("yuv_cr_acc", pix_cr)
                else:
                    out_y_val = pix_y
                    out_cb = pix_cb
                    out_cr = pix_cr
                    ctx.set_state("yuv_cb_acc", cb_acc + pix_cb)
                    ctx.set_state("yuv_cr_acc", cr_acc + pix_cr)
                ctx.set_state("yuv_x_cnt", (x_cnt + 1) % 2)

            # --- Final outputs ---
            ctx.set_output("pix_valid_o", emit)
            ctx.set_output("pix_y_o", out_y_val)
            ctx.set_output("pix_cb_o", out_cb)
            ctx.set_output("pix_cr_o", out_cr)
            ctx.set_output("pix_sof_o", pix_sof)
            ctx.set_output("pix_eol_o", pix_eol)

            # AXI-Stream output packing
            if emit:
                ctx.set_output("m_axis_tdata", (out_cr << 16) | (out_cb << 8) | out_y_val)
                ctx.set_output("m_axis_tvalid", 1)
                ctx.set_output("m_axis_tlast", pix_eol)
                ctx.set_output("m_axis_tuser", pix_sof)
            else:
                ctx.set_output("m_axis_tvalid", 0)

            # Frame tracking state
            ctx.set_state("frame_row", row)
            ctx.set_state("frame_col", col)

        return behavior

    def create_testbench(self, **kwargs) -> List[Dict]:
        """Generate basic ISP pipeline test sequences."""
        tests = []

        # Test 1: Reset / SOF
        tests.append({
            "name": "sof_reset",
            "setup": {"pix_sof_i": 1, "pix_valid_i": 0},
            "cycles": 1,
            "check": {"awb_pix_count": 0, "ae_pix_count": 0},
        })

        # Test 2: Single pixel passthrough (all modules disabled)
        tests.append({
            "name": "pixel_passthrough",
            "setup": {
                "pix_valid_i": 1, "pix_data_i": 512,
                "pix_sof_i": 0, "pix_eol_i": 0,
                "cfg_blc_enable": 0, "cfg_dg_enable": 0,
                "cfg_lsc_enable": 0, "cfg_wb_enable": 0,
                "cfg_demosaic_enable": 0, "cfg_ccm_enable": 0,
                "cfg_gamma_enable": 0, "cfg_csc_enable": 0,
                "cfg_sharpen_enable": 0, "cfg_nr2d_enable": 0,
                "cfg_scale_enable": 0, "cfg_scale_x": 0, "cfg_scale_y": 0,
            },
            "cycles": 1,
            "check": {"m_axis_tvalid": 1},
        })

        # Test 3: AWB stats accumulation
        tests.append({
            "name": "awb_accumulation",
            "setup": {
                "pix_valid_i": 1, "pix_data_i": 256,
                "pix_sof_i": 0, "pix_eol_i": 0,
                "cfg_awb_enable": 1,
                "cfg_demosaic_enable": 0, "cfg_ccm_enable": 0,
            },
            "cycles": 1,
            "check": {"awb_pix_count": 1},
        })

        return tests


__all__ = ["ISPModel"]
