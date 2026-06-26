"""
Cycle-level models for skills.image
"""
from __future__ import annotations
from typing import Any, Callable
from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


def isp_axi_in_template(**kwargs) -> Callable[[CycleContext], None]:
    """AXI-Stream slave input: tvalid/tready handshake → pix_valid/pix_data."""

    def behavior(ctx: CycleContext):
        tvalid = ctx.get_input("s_axis_tvalid", 0)
        tready_next = ctx.get_state("tready", 1)
        tdata = ctx.get_input("s_axis_tdata", 0)
        tlast = ctx.get_input("s_axis_tlast", 0)
        tuser = ctx.get_input("s_axis_tuser", 0)

        valid0 = ctx.get_state("valid0", 0)
        valid1 = ctx.get_state("valid1", 0)

        tready = 1 if not valid1 else 0

        # Output stage
        ctx.set_output("pix_valid_o", valid0)
        ctx.set_output("pix_data_o", ctx.get_state("fifo0", 0))
        ctx.set_output("pix_sof_o", ctx.get_state("sof0", 0))
        ctx.set_output("pix_eol_o", ctx.get_state("eol0", 0))
        ctx.set_output("s_axis_tready", tready)

        # Pipeline update
        if tvalid and tready:
            ctx.set_state("fifo0", tdata)
            ctx.set_state("valid0", 1)
            ctx.set_state("sof0", tuser)
            ctx.set_state("eol0", tlast)
            ctx.set_state("fifo1", tdata)
            ctx.set_state("valid1", 1)
        elif valid1:
            ctx.set_state("fifo0", ctx.get_state("fifo1", 0))
            ctx.set_state("valid0", 1)
            ctx.set_state("sof0", 0)
            ctx.set_state("eol0", 0)
            ctx.set_state("valid1", 0)
        else:
            ctx.set_state("valid0", 0)

    return behavior


# =====================================================================
# ISPCrop Template
# =====================================================================


def isp_crop_template(
    max_width: int = 2592,
    max_height: int = 1536,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Bayer-safe cropping: configurable start x/y, output w/h."""

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_data = ctx.get_input("pix_data_i", 0)
        pix_sof = ctx.get_input("pix_sof_i", 0)
        pix_eol = ctx.get_input("pix_eol_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        start_x = ctx.get_input("cfg_start_x", 0)
        start_y = ctx.get_input("cfg_start_y", 0)
        width = ctx.get_input("cfg_width", max_width)
        height = ctx.get_input("cfg_height", max_height)

        x_cnt = ctx.get_state("x_cnt", 0)
        y_cnt = ctx.get_state("y_cnt", 0)

        in_region = (
            (x_cnt >= start_x) and (x_cnt < start_x + width)
            and (y_cnt >= start_y) and (y_cnt < start_y + height)
        )

        out_valid = pix_valid and enable and in_region

        ctx.set_output("pix_valid_o", out_valid)
        ctx.set_output("pix_data_o", pix_data)
        ctx.set_output("pix_sof_o", pix_sof)
        ctx.set_output("pix_eol_o", pix_eol)

        if pix_valid:
            if pix_eol:
                ctx.set_state("x_cnt", 0)
                ctx.set_state("y_cnt", (y_cnt + 1) % max_height)
            else:
                ctx.set_state("x_cnt", (x_cnt + 1) % max_width)
            if pix_sof:
                ctx.set_state("y_cnt", 0)

    return behavior


# =====================================================================
# ISPDPC Template (Dynamic Dead Pixel Correction)
# =====================================================================


def isp_dpc_template(
    threshold: int = 100,
    raw_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """5×5 dynamic DPC: 8-direction gradient, min-gradient mean correction.

    Detects dead pixels by checking if center is outside [min, max] of
    8 footprint pixels AND all 8 diffs exceed threshold.
    Corrects using mean of min-gradient direction (V/H/LD/RD).
    """
    pixel_max = (1 << raw_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_data = ctx.get_input("pix_data_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        cfg_threshold = ctx.get_input("cfg_threshold", threshold)

        # Simplified: process single pixel (full 5×5 requires line buffers)
        center = ctx.get_state("center_buf", 0)
        ring_buf = ctx.get_state("ring_buf", [0] * 8)
        out_valid = ctx.get_state("out_valid", 0)

        if pix_valid:
            # Shift ring buffer
            ring_buf = [center] + ring_buf[:7]

            if out_valid:
                # Check 8 footprint pixels (simplified: use ring buffer)
                p = ring_buf[:8] if len(ring_buf) >= 8 else [center] * 8

                min_val = min(p)
                max_val = max(p)

                cond1 = (center < min_val) or (center > max_val)

                all_above_thresh = all(abs(center - pi) > cfg_threshold for pi in p)
                cond2 = all_above_thresh

                dead_pixel = cond1 and cond2

                # 4-direction gradients
                gv = abs(2 * center - (p[1] if len(p) > 1 else center) - (p[5] if len(p) > 5 else center))
                gh = abs(2 * center - (p[3] if len(p) > 3 else center) - (p[7] if len(p) > 7 else center))
                gld = abs(2 * center - (p[2] if len(p) > 2 else center) - (p[6] if len(p) > 6 else center))
                grd = abs(2 * center - (p[0] if len(p) > 0 else center) - (p[4] if len(p) > 4 else center))

                mean_v = ((p[1] if len(p) > 1 else center) + (p[5] if len(p) > 5 else center)) >> 1
                mean_h = ((p[3] if len(p) > 3 else center) + (p[7] if len(p) > 7 else center)) >> 1
                mean_ld = ((p[2] if len(p) > 2 else center) + (p[6] if len(p) > 6 else center)) >> 1
                mean_rd = ((p[0] if len(p) > 0 else center) + (p[4] if len(p) > 4 else center)) >> 1

                min_grad = min(gv, gh, gld, grd)
                if min_grad == gv:
                    corrected = mean_v
                elif min_grad == gh:
                    corrected = mean_h
                elif min_grad == gld:
                    corrected = mean_ld
                else:
                    corrected = mean_rd

                out_data = corrected if dead_pixel and enable else center
                ctx.set_output("pix_data_o", out_data & pixel_max)
            else:
                ctx.set_output("pix_data_o", center)

            ctx.set_state("center_buf", pix_data)
            ctx.set_state("out_valid", 1)
            ctx.set_state("ring_buf", ring_buf)
        else:
            ctx.set_output("pix_data_o", center)
            ctx.set_state("out_valid", 0)

        ctx.set_output("pix_valid_o", out_valid and enable)
        ctx.set_output("pix_sof_o", ctx.get_state("out_sof", 0))
        ctx.set_output("pix_eol_o", ctx.get_state("out_eol", 0))

        if pix_valid:
            ctx.set_state("out_sof", ctx.get_input("pix_sof_i", 0))
            ctx.set_state("out_eol", ctx.get_input("pix_eol_i", 0))

    return behavior


# =====================================================================
# ISPBLC Template (Black Level Correction)
# =====================================================================


def isp_blc_template(
    raw_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Per-channel Bayer black level offset subtraction.

    Selects offset based on Bayer pattern (RGGB/BGGR/GRBG/GBRG)
    and row/col parity. Clips result to [0, pixel_max].
    """
    pixel_max = (1 << raw_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_data = ctx.get_input("pix_data_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        r_off = ctx.get_input("cfg_r_offset", 0)
        gr_off = ctx.get_input("cfg_gr_offset", 0)
        gb_off = ctx.get_input("cfg_gb_offset", 0)
        b_off = ctx.get_input("cfg_b_offset", 0)
        bayer = ctx.get_input("cfg_bayer", 0)

        row = ctx.get_state("row", 0)
        col = ctx.get_state("col", 0)

        # Select offset based on Bayer pattern and position
        if bayer == 0:  # RGGB
            offset = r_off if (row == 0 and col == 0) else \
                     gr_off if (row == 0) else \
                     gb_off if (col == 0) else b_off
        elif bayer == 1:  # BGGR
            offset = b_off if (row == 0 and col == 0) else \
                     gb_off if (row == 0) else \
                     gr_off if (col == 0) else r_off
        elif bayer == 2:  # GRBG
            offset = gr_off if (row == 0 and col == 0) else \
                     r_off if (row == 0) else \
                     b_off if (col == 0) else gb_off
        else:  # GBRG
            offset = gb_off if (row == 0 and col == 0) else \
                     b_off if (row == 0) else \
                     r_off if (col == 0) else gr_off

        sub = pix_data - offset
        result = max(0, min(sub, pixel_max))

        ctx.set_output("pix_valid_o", pix_valid and enable)
        ctx.set_output("pix_data_o", result)
        ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
        ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))

        if pix_valid:
            if ctx.get_input("pix_eol_i", 0):
                ctx.set_state("col", 0)
                ctx.set_state("row", 1 - row)
            else:
                ctx.set_state("col", 1 - col)

    return behavior


# =====================================================================
# ISPOECF Template
# =====================================================================


def isp_oecf_template(
    lut_depth: int = 256,
    raw_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Opto-Electronic Conversion Function: per-channel LUT mapping.

    Uses top 8 bits of 12-bit pixel as LUT index.
    """
    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_data = ctx.get_input("pix_data_i", 0)
        enable = ctx.get_input("cfg_enable", 1)

        # LUT index from top 8 bits
        lut_idx = pix_data >> (raw_width - 8)
        lut_val = ctx.get_state(f"oecf_lut_{lut_idx}", lut_idx)  # passthrough by default

        ctx.set_output("pix_valid_o", pix_valid and enable)
        ctx.set_output("pix_data_o", lut_val)
        ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
        ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))

    return behavior


# =====================================================================
# ISPDG Template (Digital Gain)
# =====================================================================


def isp_dg_template(
    raw_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Digital Gain: Q4.8 fixed-point multiplication with saturation.

    gain = cfg_gain / 256. result = pix * gain, clipped to [0, pixel_max].
    AE feedback can auto-adjust gain.
    """
    pixel_max = (1 << raw_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_data = ctx.get_input("pix_data_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        gain = ctx.get_input("cfg_gain", 256)  # Q4.8, 256 = 1.0x

        prod = pix_data * gain
        shifted = prod >> 8
        result = min(shifted, pixel_max)

        ctx.set_output("pix_valid_o", pix_valid and enable)
        ctx.set_output("pix_data_o", result)
        ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
        ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))

    return behavior


# =====================================================================
# ISPLSC Template (Lens Shading Correction)
# =====================================================================


def isp_lsc_template(
    raw_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Lens Shading Correction: per-channel radial gain model.

    Selects gain based on Bayer pattern and row/col parity.
    gain is Q4.4 fixed point. result = pix * gain >> 4, clipped.
    """
    pixel_max = (1 << raw_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_data = ctx.get_input("pix_data_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        gain_r = ctx.get_input("cfg_gain_r", 16)
        gain_gr = ctx.get_input("cfg_gain_gr", 16)
        gain_gb = ctx.get_input("cfg_gain_gb", 16)
        gain_b = ctx.get_input("cfg_gain_b", 16)
        bayer = ctx.get_input("cfg_bayer", 0)

        row = ctx.get_state("row", 0)
        col = ctx.get_state("col", 0)

        if bayer == 0:  # RGGB
            gain_sel = gain_r if (row == 0 and col == 0) else \
                       gain_gr if (row == 0) else \
                       gain_gb if (col == 0) else gain_b
        elif bayer == 1:  # BGGR
            gain_sel = gain_b if (row == 0 and col == 0) else \
                       gain_gb if (row == 0) else \
                       gain_gr if (col == 0) else gain_r
        elif bayer == 2:  # GRBG
            gain_sel = gain_gr if (row == 0 and col == 0) else \
                       gain_r if (row == 0) else \
                       gain_b if (col == 0) else gain_gb
        else:  # GBRG
            gain_sel = gain_gb if (row == 0 and col == 0) else \
                       gain_b if (row == 0) else \
                       gain_r if (col == 0) else gain_gr

        prod = pix_data * gain_sel
        shifted = prod >> 4
        result = min(shifted, pixel_max)

        ctx.set_output("pix_valid_o", pix_valid and enable)
        ctx.set_output("pix_data_o", result)
        ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
        ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))

        if pix_valid:
            if ctx.get_input("pix_eol_i", 0):
                ctx.set_state("col", 0)
                ctx.set_state("row", 1 - row)
            else:
                ctx.set_state("col", 1 - col)

    return behavior


# =====================================================================
# ISPBNR Template (Bayer Noise Reduction)
# =====================================================================


def isp_bnr_template(
    sigma_r: int = 64,
    raw_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Bayer Noise Reduction: Joint Bilateral Filter with Green Guiding.

    5×5 spatial Gaussian weights combined with range kernel LUT.
    Only same-color pixels contribute to the filtered output.
    """
    pixel_max = (1 << raw_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_data = ctx.get_input("pix_data_i", 0)
        enable = ctx.get_input("cfg_enable", 1)

        center = ctx.get_state("center_buf", 0)
        out_valid = ctx.get_state("out_valid", 0)

        if pix_valid and out_valid:
            # Simplified: Gaussian smoothing with configurable sigma
            # Full implementation uses 5×5 joint bilateral with range LUT
            neighbors = ctx.get_state("neighbors", [center] * 8)
            weights = [1, 4, 7, 4, 1, 4, 16, 26]  # simplified spatial weights

            weighted_sum = center * 41  # center weight
            weight_total = 41
            for i, (n, w) in enumerate(zip(neighbors[:8], weights)):
                diff = abs(center - n)
                range_w = max(0, 16 - (diff >> 4))  # simplified range weight
                combined = (w * range_w) >> 4
                weighted_sum += combined * n
                weight_total += combined

            if weight_total > 0:
                result = weighted_sum // weight_total
            else:
                result = center

            result = min(result, pixel_max)
            ctx.set_output("pix_data_o", result)
            ctx.set_state("center_buf", pix_data)
            ctx.set_state("neighbors", [center] + neighbors[:7])
        else:
            ctx.set_output("pix_data_o", center)
            if pix_valid:
                ctx.set_state("center_buf", pix_data)
                ctx.set_state("out_valid", 1)

        ctx.set_output("pix_valid_o", out_valid and enable)
        ctx.set_output("pix_sof_o", ctx.get_state("out_sof", 0))
        ctx.set_output("pix_eol_o", ctx.get_state("out_eol", 0))

        if pix_valid:
            ctx.set_state("out_sof", ctx.get_input("pix_sof_i", 0))
            ctx.set_state("out_eol", ctx.get_input("pix_eol_i", 0))

    return behavior


# =====================================================================
# ISPWB Template (White Balance)
# =====================================================================


def isp_wb_template(
    raw_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """White Balance: Bayer domain per-channel gain (Q4.8).

    Selects R/G/B gain based on Bayer pattern and row/col parity.
    AWB stats module computes optimal gains from RGB histogram.
    """
    pixel_max = (1 << raw_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_data = ctx.get_input("pix_data_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        r_gain = ctx.get_input("cfg_r_gain", 256)
        g_gain = ctx.get_input("cfg_g_gain", 256)
        b_gain = ctx.get_input("cfg_b_gain", 256)
        bayer = ctx.get_input("cfg_bayer", 0)

        row = ctx.get_state("row", 0)
        col = ctx.get_state("col", 0)

        # Determine channel
        if bayer == 0:  # RGGB
            is_r = (row == 0 and col == 0)
            is_b = (row == 1 and col == 1)
        elif bayer == 1:  # BGGR
            is_r = (row == 1 and col == 1)
            is_b = (row == 0 and col == 0)
        elif bayer == 2:  # GRBG
            is_r = (row == 0 and col == 1)
            is_b = (row == 1 and col == 0)
        else:  # GBRG
            is_r = (row == 1 and col == 0)
            is_b = (row == 0 and col == 1)

        gain_sel = r_gain if is_r else (b_gain if is_b else g_gain)
        prod = pix_data * gain_sel
        shifted = prod >> 8
        result = min(shifted, pixel_max)

        ctx.set_output("pix_valid_o", pix_valid and enable)
        ctx.set_output("pix_data_o", result)
        ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
        ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))

        if pix_valid:
            if ctx.get_input("pix_eol_i", 0):
                ctx.set_state("col", 0)
                ctx.set_state("row", 1 - row)
            else:
                ctx.set_state("col", 1 - col)

    return behavior


# =====================================================================
# ISPAWBStats Template
# =====================================================================


def isp_awb_stats_template(**kwargs) -> Callable[[CycleContext], None]:
    """Auto White Balance Statistics: RGB channel sum accumulation.

    Accumulates R, G, B sums over the frame for AWB gain computation.
    Resets on SOF.
    """

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_r = ctx.get_input("pix_r_i", 0)
        pix_g = ctx.get_input("pix_g_i", 0)
        pix_b = ctx.get_input("pix_b_i", 0)
        pix_sof = ctx.get_input("pix_sof_i", 0)
        enable = ctx.get_input("cfg_enable", 1)

        r_acc = ctx.get_state("r_acc", 0)
        g_acc = ctx.get_state("g_acc", 0)
        b_acc = ctx.get_state("b_acc", 0)
        cnt = ctx.get_state("cnt", 0)

        if pix_sof:
            r_acc = 0
            g_acc = 0
            b_acc = 0
            cnt = 0

        if pix_valid and enable:
            r_acc += pix_r
            g_acc += pix_g
            b_acc += pix_b
            cnt += 1

        ctx.set_output("stat_r_sum", r_acc)
        ctx.set_output("stat_g_sum", g_acc)
        ctx.set_output("stat_b_sum", b_acc)
        ctx.set_output("stat_pix_count", cnt)
        ctx.set_output("stat_done", 1 if cnt > 0 else 0)

        ctx.set_state("r_acc", r_acc)
        ctx.set_state("g_acc", g_acc)
        ctx.set_state("b_acc", b_acc)
        ctx.set_state("cnt", cnt)

    return behavior


# =====================================================================
# ISPDemosaic Template (Malvar-He-Cutler)
# =====================================================================


def isp_demosaic_template(
    raw_width: int = 12,
    rgb_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Malvar-He-Cutler 5×5 CFA interpolation.

    Converts Bayer RAW to full RGB using integer filter kernels:
    - G at R/B: (4*center + 2*(N+S+E+W) - (NN+SS+EE+WW)) / 8
    - R at Gr/B at Gb: asymmetric 5×5 kernel (horizontal emphasis)
    - R at Gb/B at Gr: transpose of above (vertical emphasis)
    - R at B/B at R: diagonal kernel
    """
    pixel_max = (1 << raw_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_data = ctx.get_input("pix_data_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        bayer = ctx.get_input("cfg_bayer", 0)

        center = ctx.get_state("center_buf", 0)
        out_valid = ctx.get_state("out_valid", 0)
        row = ctx.get_state("row", 0)
        col = ctx.get_state("col", 0)

        if pix_valid and out_valid:
            # Determine Bayer position
            if bayer == 0:  # RGGB
                is_r = (row == 0 and col == 0)
                is_b = (row == 1 and col == 1)
            elif bayer == 1:  # BGGR
                is_r = (row == 1 and col == 1)
                is_b = (row == 0 and col == 0)
            elif bayer == 2:  # GRBG
                is_r = (row == 0 and col == 1)
                is_b = (row == 1 and col == 0)
            else:  # GBRG
                is_r = (row == 1 and col == 0)
                is_b = (row == 0 and col == 1)

            neighbors = ctx.get_state("neighbors", [center] * 8)

            # Simplified demosaic: bilinear interpolation
            # G at R/B
            orth_sum = sum(neighbors[i] for i in [1, 3, 5, 7]) if len(neighbors) >= 8 else center * 4
            diag_sum = sum(neighbors[i] for i in [0, 2, 4, 6]) if len(neighbors) >= 8 else center * 4
            g_interp = max(0, min(((center << 2) + (orth_sum << 1) - diag_sum) >> 3, pixel_max))

            # R and B at G/B/R positions (simplified)
            r_val = center if is_r else max(0, min(((neighbors[3] if len(neighbors) > 3 else center) +
                                                     (neighbors[5] if len(neighbors) > 5 else center)) >> 1, pixel_max))
            b_val = center if is_b else max(0, min(((neighbors[1] if len(neighbors) > 1 else center) +
                                                     (neighbors[7] if len(neighbors) > 7 else center)) >> 1, pixel_max))

            if is_r:
                ctx.set_output("pix_r_o", center)
                ctx.set_output("pix_g_o", g_interp)
                ctx.set_output("pix_b_o", b_val)
            elif is_b:
                ctx.set_output("pix_r_o", r_val)
                ctx.set_output("pix_g_o", g_interp)
                ctx.set_output("pix_b_o", center)
            else:
                ctx.set_output("pix_r_o", r_val)
                ctx.set_output("pix_g_o", center)
                ctx.set_output("pix_b_o", b_val)

            ctx.set_state("center_buf", pix_data)
            ctx.set_state("neighbors", [center] + neighbors[:7])
        else:
            ctx.set_output("pix_r_o", center)
            ctx.set_output("pix_g_o", center)
            ctx.set_output("pix_b_o", center)
            if pix_valid:
                ctx.set_state("center_buf", pix_data)
                ctx.set_state("out_valid", 1)

        ctx.set_output("pix_valid_o", out_valid and enable)
        ctx.set_output("pix_sof_o", ctx.get_state("out_sof", 0))
        ctx.set_output("pix_eol_o", ctx.get_state("out_eol", 0))

        if pix_valid:
            ctx.set_state("out_sof", ctx.get_input("pix_sof_i", 0))
            ctx.set_state("out_eol", ctx.get_input("pix_eol_i", 0))
            if ctx.get_input("pix_eol_i", 0):
                ctx.set_state("col", 0)
                ctx.set_state("row", 1 - row)
            else:
                ctx.set_state("col", 1 - col)

    return behavior


# =====================================================================
# ISPCCM Template (Color Correction Matrix)
# =====================================================================


def isp_ccm_template(
    rgb_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """3×3 Color Correction Matrix: fixed-point Q4.8 signed MAC.

    [R']   [c00 c01 c02]   [R]
    [G'] = [c10 c11 c12] × [G]
    [B']   [c20 c21 c22]   [B]

    Coefficients are Q4.8 signed. Result >> 8, clipped to [0, pixel_max].
    """
    pixel_max = (1 << rgb_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_r = ctx.get_input("pix_r_i", 0)
        pix_g = ctx.get_input("pix_g_i", 0)
        pix_b = ctx.get_input("pix_b_i", 0)
        enable = ctx.get_input("cfg_enable", 1)

        c00 = ctx.get_input("cfg_c00", 256)  # 1.0 in Q4.8
        c01 = ctx.get_input("cfg_c01", 0)
        c02 = ctx.get_input("cfg_c02", 0)
        c10 = ctx.get_input("cfg_c10", 0)
        c11 = ctx.get_input("cfg_c11", 256)
        c12 = ctx.get_input("cfg_c12", 0)
        c20 = ctx.get_input("cfg_c20", 0)
        c21 = ctx.get_input("cfg_c21", 0)
        c22 = ctx.get_input("cfg_c22", 256)

        def smul(pix, coeff):
            neg = coeff & 0x800
            coeff_abs = ((~coeff + 1) & 0xFFF) if neg else coeff
            prod = pix * coeff_abs
            return (-prod) if neg else prod

        r_acc = smul(pix_r, c00) + smul(pix_g, c01) + smul(pix_b, c02)
        g_acc = smul(pix_r, c10) + smul(pix_g, c11) + smul(pix_b, c12)
        b_acc = smul(pix_r, c20) + smul(pix_g, c21) + smul(pix_b, c22)

        r_out = min(max(r_acc >> 8, 0), pixel_max)
        g_out = min(max(g_acc >> 8, 0), pixel_max)
        b_out = min(max(b_acc >> 8, 0), pixel_max)

        ctx.set_output("pix_valid_o", pix_valid and enable)
        ctx.set_output("pix_r_o", r_out)
        ctx.set_output("pix_g_o", g_out)
        ctx.set_output("pix_b_o", b_out)
        ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
        ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))

    return behavior


# =====================================================================
# ISPGamma Template
# =====================================================================


def isp_gamma_template(
    rgb_width: int = 12,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Gamma Correction: 4096-entry per-channel LUT.

    Each R/G/B channel has its own 12-bit → 12-bit mapping.
    """

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_r = ctx.get_input("pix_r_i", 0)
        pix_g = ctx.get_input("pix_g_i", 0)
        pix_b = ctx.get_input("pix_b_i", 0)
        enable = ctx.get_input("cfg_enable", 1)

        # LUT lookup (passthrough by default, programmable via init)
        r_out = ctx.get_state(f"gamma_r_{pix_r}", pix_r)
        g_out = ctx.get_state(f"gamma_g_{pix_g}", pix_g)
        b_out = ctx.get_state(f"gamma_b_{pix_b}", pix_b)

        ctx.set_output("pix_valid_o", pix_valid and enable)
        ctx.set_output("pix_r_o", r_out)
        ctx.set_output("pix_g_o", g_out)
        ctx.set_output("pix_b_o", b_out)
        ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
        ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))

    return behavior


# =====================================================================
# ISPAEStats Template
# =====================================================================


def isp_ae_stats_template(**kwargs) -> Callable[[CycleContext], None]:
    """Auto Exposure Statistics: Y histogram with skewness computation.

    Accumulates Y sum, Y² sum, and signed Y³ (for skewness).
    Center illumination weighting for region-of-interest exposure.
    """

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_y = ctx.get_input("pix_y_i", 0)
        pix_sof = ctx.get_input("pix_sof_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        center_illum = ctx.get_input("cfg_center_illum", 128)

        y_acc = ctx.get_state("y_acc", 0)
        y_sq_acc = ctx.get_state("y_sq_acc", 0)
        y_cu_acc = ctx.get_state("y_cu_acc", 0)
        cnt = ctx.get_state("cnt", 0)

        if pix_sof:
            y_acc = 0
            y_sq_acc = 0
            y_cu_acc = 0
            cnt = 0

        if pix_valid and enable:
            y_centered = abs(pix_y - center_illum)
            y_sq = y_centered * y_centered
            y_cu = y_sq * y_centered
            sign = 1 if pix_y > center_illum else -1

            y_acc += pix_y
            y_sq_acc += y_sq
            y_cu_acc += sign * y_cu
            cnt += 1

        ctx.set_output("stat_y_sum", y_acc)
        ctx.set_output("stat_y_sq_sum", y_sq_acc)
        ctx.set_output("stat_y_cu_sum", y_cu_acc)
        ctx.set_output("stat_pix_count", cnt)
        ctx.set_output("stat_done", 1 if cnt > 0 else 0)

        ctx.set_state("y_acc", y_acc)
        ctx.set_state("y_sq_acc", y_sq_acc)
        ctx.set_state("y_cu_acc", y_cu_acc)
        ctx.set_state("cnt", cnt)

    return behavior


# =====================================================================
# ISPCSC Template (Color Space Conversion)
# =====================================================================


def isp_csc_template(**kwargs) -> Callable[[CycleContext], None]:
    """RGB → YCbCr conversion: BT.601 or BT.709.

    BT.709: Y = (47R + 157G + 16B) >> 8, Cb = (-26R - 86G + 112B) >> 8 + 128
    BT.601: Y = (77R + 150G + 29B) >> 8, Cb = (-43R - 85G + 128B) >> 8 + 128
    """

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_r = ctx.get_input("pix_r_i", 0)
        pix_g = ctx.get_input("pix_g_i", 0)
        pix_b = ctx.get_input("pix_b_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        bt709 = ctx.get_input("cfg_std", 0) == 0

        r, g, b = pix_r, pix_g, pix_b
        if bt709:
            y_acc = 47 * r + 157 * g + 16 * b
            cb_acc = -26 * r - 86 * g + 112 * b
            cr_acc = 112 * r - 102 * g - 10 * b
        else:
            y_acc = 77 * r + 150 * g + 29 * b
            cb_acc = -43 * r - 85 * g + 128 * b
            cr_acc = 128 * r - 107 * g - 21 * b

        y_val = min(max(y_acc >> 8, 0), 255)
        cb_val = min(max((cb_acc >> 8) + 128, 0), 255)
        cr_val = min(max((cr_acc >> 8) + 128, 0), 255)

        ctx.set_output("pix_valid_o", pix_valid and enable)
        ctx.set_output("pix_y_o", y_val)
        ctx.set_output("pix_cb_o", cb_val)
        ctx.set_output("pix_cr_o", cr_val)
        ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
        ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))

    return behavior


# =====================================================================
# ISPLDCI Template (CLAHE)
# =====================================================================


def isp_ldci_template(
    num_tiles_x: int = 8,
    num_tiles_y: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """CLAHE: Contrast Limited Adaptive Histogram Equalization.

    Tile-based (8×8 grid): histogram accumulation → CDF computation
    → LUT application. Ping-pong buffered LUTs for frame-to-frame.
    """

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_y = ctx.get_input("pix_y_i", 0)
        pix_cb = ctx.get_input("pix_cb_i", 0)
        pix_cr = ctx.get_input("pix_cr_i", 0)
        pix_sof = ctx.get_input("pix_sof_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        clip_limit = ctx.get_input("cfg_clip_limit", 1024)

        state = ctx.get_state("state", 0)  # 0=IDLE, 1=HIST, 2=CDF, 3=APPLY
        frame_started = ctx.get_state("frame_started", 0)

        if pix_sof and state == 0:
            state = 1  # HIST
            frame_started = 1

        if state == 3:  # APPLY
            # LUT-mapped Y output (simplified: passthrough)
            y_out = pix_y
            ctx.set_output("pix_valid_o", pix_valid and enable)
            ctx.set_output("pix_y_o", y_out)
            ctx.set_output("pix_cb_o", pix_cb)
            ctx.set_output("pix_cr_o", pix_cr)
            ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
            ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))
            if pix_sof:
                state = 1  # next frame HIST
        else:
            ctx.set_output("pix_valid_o", pix_valid and enable)
            ctx.set_output("pix_y_o", pix_y)
            ctx.set_output("pix_cb_o", pix_cb)
            ctx.set_output("pix_cr_o", pix_cr)
            ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
            ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))
            if state == 1 and pix_valid:
                # Histogram accumulation (simplified)
                pass
            if state == 1 and ctx.get_input("pix_eol_i", 0):
                # Frame end → CDF computation
                state = 2
            if state == 2:
                # CDF computation done → APPLY
                state = 3

        ctx.set_state("state", state)
        ctx.set_state("frame_started", frame_started)

    return behavior


# =====================================================================
# ISPSharpen Template (Unsharp Masking)
# =====================================================================


def isp_sharpen_template(
    yuv_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Unsharp Masking: Gaussian 3×3 smoothing + detail enhancement.

    Gaussian kernel [1,2,1; 2,4,2; 1,2,1] (sum=16).
    detail = original - smoothed
    sharpened = original + detail * strength (Q4.4)
    """
    pixel_max = (1 << yuv_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_y = ctx.get_input("pix_y_i", 0)
        pix_cb = ctx.get_input("pix_cb_i", 0)
        pix_cr = ctx.get_input("pix_cr_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        strength = ctx.get_input("cfg_strength", 16)  # Q4.4, 16 = 1.0

        center = ctx.get_state("center_buf", 0)
        out_valid = ctx.get_state("out_valid", 0)

        if pix_valid and out_valid:
            neighbors = ctx.get_state("neighbors", [center] * 8)
            # 3×3 Gaussian: sum of neighbors with weights
            corners = sum(neighbors[i] for i in [0, 2, 4, 6]) if len(neighbors) >= 8 else center * 4
            edges = sum(neighbors[i] for i in [1, 3, 5, 7]) if len(neighbors) >= 8 else center * 4
            smoothed = (corners + (edges << 1) + (center << 2)) >> 4

            detail = center - smoothed
            scaled_detail = (detail * strength) >> 4
            sharp_y = min(max(center + scaled_detail, 0), pixel_max)

            ctx.set_output("pix_y_o", sharp_y)
            ctx.set_state("center_buf", pix_y)
            ctx.set_state("neighbors", [center] + neighbors[:7])
        else:
            ctx.set_output("pix_y_o", center)
            if pix_valid:
                ctx.set_state("center_buf", pix_y)
                ctx.set_state("out_valid", 1)

        ctx.set_output("pix_valid_o", out_valid and enable)
        ctx.set_output("pix_cb_o", ctx.get_state("out_cb", 0))
        ctx.set_output("pix_cr_o", ctx.get_state("out_cr", 0))
        ctx.set_output("pix_sof_o", ctx.get_state("out_sof", 0))
        ctx.set_output("pix_eol_o", ctx.get_state("out_eol", 0))

        if pix_valid:
            ctx.set_state("out_cb", pix_cb)
            ctx.set_state("out_cr", pix_cr)
            ctx.set_state("out_sof", ctx.get_input("pix_sof_i", 0))
            ctx.set_state("out_eol", ctx.get_input("pix_eol_i", 0))

    return behavior


# =====================================================================
# ISPNR2D Template (2D Noise Reduction)
# =====================================================================


def isp_nr2d_template(
    yuv_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """2D Noise Reduction: Y-channel Gaussian smoothing blend.

    3×3 box filter blended with original based on strength (Q4.4).
    output = (original * (16 - strength) + smooth * strength) >> 4
    """
    pixel_max = (1 << yuv_width) - 1

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_y = ctx.get_input("pix_y_i", 0)
        pix_cb = ctx.get_input("pix_cb_i", 0)
        pix_cr = ctx.get_input("pix_cr_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        strength = ctx.get_input("cfg_strength", 4)  # Q4.4

        center = ctx.get_state("center_buf", 0)
        out_valid = ctx.get_state("out_valid", 0)

        if pix_valid and out_valid:
            neighbors = ctx.get_state("neighbors", [center] * 8)
            smooth = (center + sum(neighbors[:8])) >> 3
            blend = (center * (16 - strength) + smooth * strength) >> 4
            blend = min(max(blend, 0), pixel_max)

            ctx.set_output("pix_y_o", blend)
            ctx.set_state("center_buf", pix_y)
            ctx.set_state("neighbors", [center] + neighbors[:7])
        else:
            ctx.set_output("pix_y_o", center)
            if pix_valid:
                ctx.set_state("center_buf", pix_y)
                ctx.set_state("out_valid", 1)

        ctx.set_output("pix_valid_o", out_valid and enable)
        ctx.set_output("pix_cb_o", ctx.get_state("out_cb", 0))
        ctx.set_output("pix_cr_o", ctx.get_state("out_cr", 0))
        ctx.set_output("pix_sof_o", ctx.get_state("out_sof", 0))
        ctx.set_output("pix_eol_o", ctx.get_state("out_eol", 0))

        if pix_valid:
            ctx.set_state("out_cb", pix_cb)
            ctx.set_state("out_cr", pix_cr)
            ctx.set_state("out_sof", ctx.get_input("pix_sof_i", 0))
            ctx.set_state("out_eol", ctx.get_input("pix_eol_i", 0))

    return behavior


# =====================================================================
# ISPScale Template
# =====================================================================


def isp_scale_template(**kwargs) -> Callable[[CycleContext], None]:
    """Image scaling: nearest-neighbor downsampling.

    cfg_scale_x/y: 0=1x, 1=1/2x (skip odd pixels), 2=1/4x (skip 3 of 4).
    """

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_y = ctx.get_input("pix_y_i", 0)
        pix_cb = ctx.get_input("pix_cb_i", 0)
        pix_cr = ctx.get_input("pix_cr_i", 0)
        pix_sof = ctx.get_input("pix_sof_i", 0)
        pix_eol = ctx.get_input("pix_eol_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        scale_x = ctx.get_input("cfg_scale_x", 0)
        scale_y = ctx.get_input("cfg_scale_y", 0)

        x_cnt = ctx.get_state("x_cnt", 0)
        y_cnt = ctx.get_state("y_cnt", 0)

        # Output pixel selection
        out_x = True if scale_x == 0 else \
                (x_cnt % 2 == 0) if scale_x == 1 else \
                (x_cnt % 4 == 0)
        out_y = True if scale_y == 0 else \
                (y_cnt % 2 == 0) if scale_y == 1 else \
                (y_cnt % 4 == 0)

        emit = pix_valid and enable and out_x and out_y

        ctx.set_output("pix_valid_o", emit)
        ctx.set_output("pix_y_o", pix_y)
        ctx.set_output("pix_cb_o", pix_cb)
        ctx.set_output("pix_cr_o", pix_cr)
        ctx.set_output("pix_sof_o", pix_sof)
        ctx.set_output("pix_eol_o", pix_eol and out_x)

        if pix_valid:
            if pix_eol:
                ctx.set_state("x_cnt", 0)
                ctx.set_state("y_cnt", y_cnt + 1)
            else:
                ctx.set_state("x_cnt", x_cnt + 1)
            if pix_sof:
                ctx.set_state("y_cnt", 0)

    return behavior


# =====================================================================
# ISPYUV Template
# =====================================================================


def isp_yuv_template(**kwargs) -> Callable[[CycleContext], None]:
    """YUV format conversion: 444 passthrough or 422/420 chroma subsampling.

    422: average Cb/Cr across 2 horizontal pixels.
    420: additionally average across 2 vertical lines.
    """

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_y = ctx.get_input("pix_y_i", 0)
        pix_cb = ctx.get_input("pix_cb_i", 0)
        pix_cr = ctx.get_input("pix_cr_i", 0)
        enable = ctx.get_input("cfg_enable", 1)
        fmt = ctx.get_input("cfg_format", 0)  # 0=444, 1=422, 2=420

        x_cnt = ctx.get_state("x_cnt", 0)
        y_cnt = ctx.get_state("y_cnt", 0)
        cb_acc = ctx.get_state("cb_acc", 0)
        cr_acc = ctx.get_state("cr_acc", 0)

        if fmt == 0:  # 444 passthrough
            ctx.set_output("pix_valid_o", pix_valid and enable)
            ctx.set_output("pix_y_o", pix_y)
            ctx.set_output("pix_cb_o", pix_cb)
            ctx.set_output("pix_cr_o", pix_cr)
        else:  # 422/420: chroma averaging
            if x_cnt == 0:
                ctx.set_output("pix_valid_o", pix_valid and enable)
                ctx.set_output("pix_y_o", pix_y)
                ctx.set_output("pix_cb_o", cb_acc >> 1)
                ctx.set_output("pix_cr_o", cr_acc >> 1)
                ctx.set_state("cb_acc", pix_cb)
                ctx.set_state("cr_acc", pix_cr)
            else:
                ctx.set_output("pix_valid_o", pix_valid and enable)
                ctx.set_output("pix_y_o", pix_y)
                ctx.set_output("pix_cb_o", pix_cb)
                ctx.set_output("pix_cr_o", pix_cr)
                ctx.set_state("cb_acc", cb_acc + pix_cb)
                ctx.set_state("cr_acc", cr_acc + pix_cr)

        ctx.set_output("pix_sof_o", ctx.get_input("pix_sof_i", 0))
        ctx.set_output("pix_eol_o", ctx.get_input("pix_eol_i", 0))

        if pix_valid:
            if ctx.get_input("pix_eol_i", 0):
                ctx.set_state("x_cnt", 0)
                ctx.set_state("y_cnt", 1 - y_cnt)
            else:
                ctx.set_state("x_cnt", 1 - x_cnt)

    return behavior


# =====================================================================
# ISPAXIStreamOut Template
# =====================================================================


def isp_axi_out_template(
    output_width: int = 24,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """AXI-Stream master output: internal pixel stream → AXI-Stream.

    Packs Y/Cb/Cr into 24-bit tdata. tvalid/tready handshake.
    """

    def behavior(ctx: CycleContext):
        pix_valid = ctx.get_input("pix_valid_i", 0)
        pix_y = ctx.get_input("pix_y_i", 0)
        pix_cb = ctx.get_input("pix_cb_i", 0)
        pix_cr = ctx.get_input("pix_cr_i", 0)
        pix_sof = ctx.get_input("pix_sof_i", 0)
        pix_eol = ctx.get_input("pix_eol_i", 0)
        m_ready = ctx.get_input("m_axis_tready", 1)

        out_valid = ctx.get_state("out_valid", 0)

        # AXI-Stream outputs
        ctx.set_output("m_axis_tvalid", out_valid)
        ctx.set_output("m_axis_tdata", ctx.get_state("out_reg", 0))
        ctx.set_output("m_axis_tlast", ctx.get_state("out_last", 0))
        ctx.set_output("m_axis_tuser", ctx.get_state("out_user", 0))

        if pix_valid and m_ready:
            ctx.set_state("out_reg", (pix_cr << 16) | (pix_cb << 8) | pix_y)
            ctx.set_state("out_valid", 1)
            ctx.set_state("out_last", pix_eol)
            ctx.set_state("out_user", pix_sof)
        elif m_ready:
            ctx.set_state("out_valid", 0)

    return behavior


# =====================================================================
# ISPAPBRegs Template
# =====================================================================


def isp_apb_regs_template(
    num_regs: int = 32,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """APB Configuration Register Bank: 32×32-bit registers with field decode.

    APB 2-cycle access (setup + enable). Write to reg[addr>>2],
    read from reg[addr>>2]. Field decoding maps bits to module configs.
    """

    def behavior(ctx: CycleContext):
        psel = ctx.get_input("psel", 0)
        penable = ctx.get_input("penable", 0)
        pwrite = ctx.get_input("pwrite", 0)
        paddr = ctx.get_input("paddr", 0)
        pwdata = ctx.get_input("pwdata", 0)

        addr_idx = (paddr >> 2) & 0x1F

        # Read data
        prdata = ctx.get_state(f"reg_{addr_idx}", 0)
        pready = psel and penable

        # Write
        if psel and penable and pwrite:
            ctx.set_state(f"reg_{addr_idx}", pwdata)

        # Decode common fields from registers
        cfg_crop_enable = ctx.get_state("reg_0", 0) & 0x1
        cfg_dpc_enable = (ctx.get_state("reg_1", 0) >> 0) & 0x1
        cfg_blc_enable = (ctx.get_state("reg_1", 0) >> 8) & 0x1
        cfg_dg_enable = (ctx.get_state("reg_3", 0) >> 0) & 0x1
        cfg_wb_enable = (ctx.get_state("reg_4", 0) >> 0) & 0x1
        cfg_demosaic_enable = (ctx.get_state("reg_5", 0) >> 14) & 0x1
        cfg_ccm_enable = (ctx.get_state("reg_5", 0) >> 15) & 0x1
        cfg_csc_enable = (ctx.get_state("reg_5", 0) >> 0) & 0x1
        cfg_gamma_enable = (ctx.get_state("reg_5", 0) >> 16) & 0x1

        ctx.set_output("prdata", prdata)
        ctx.set_output("pready", pready)
        ctx.set_output("pslverr", 0)
        ctx.set_output("cfg_crop_enable", cfg_crop_enable)
        ctx.set_output("cfg_dpc_enable", cfg_dpc_enable)
        ctx.set_output("cfg_blc_enable", cfg_blc_enable)
        ctx.set_output("cfg_dg_enable", cfg_dg_enable)
        ctx.set_output("cfg_wb_enable", cfg_wb_enable)
        ctx.set_output("cfg_demosaic_enable", cfg_demosaic_enable)
        ctx.set_output("cfg_ccm_enable", cfg_ccm_enable)
        ctx.set_output("cfg_csc_enable", cfg_csc_enable)
        ctx.set_output("cfg_gamma_enable", cfg_gamma_enable)

    return behavior


# Register ISP templates
TemplateRegistry.register("isp_axi_in", isp_axi_in_template)
TemplateRegistry.register("isp_crop", isp_crop_template)
TemplateRegistry.register("isp_dpc", isp_dpc_template)
TemplateRegistry.register("isp_blc", isp_blc_template)
TemplateRegistry.register("isp_oecf", isp_oecf_template)
TemplateRegistry.register("isp_dg", isp_dg_template)
TemplateRegistry.register("isp_lsc", isp_lsc_template)
TemplateRegistry.register("isp_bnr", isp_bnr_template)
TemplateRegistry.register("isp_wb", isp_wb_template)
TemplateRegistry.register("isp_awb_stats", isp_awb_stats_template)
TemplateRegistry.register("isp_demosaic", isp_demosaic_template)
TemplateRegistry.register("isp_ccm", isp_ccm_template)
TemplateRegistry.register("isp_gamma", isp_gamma_template)
TemplateRegistry.register("isp_ae_stats", isp_ae_stats_template)
TemplateRegistry.register("isp_csc", isp_csc_template)
TemplateRegistry.register("isp_ldci", isp_ldci_template)
TemplateRegistry.register("isp_sharpen", isp_sharpen_template)
TemplateRegistry.register("isp_nr2d", isp_nr2d_template)
TemplateRegistry.register("isp_scale", isp_scale_template)
TemplateRegistry.register("isp_yuv", isp_yuv_template)
TemplateRegistry.register("isp_axi_out", isp_axi_out_template)
TemplateRegistry.register("isp_apb_regs", isp_apb_regs_template)

__all__ = [
    "isp_axi_in_template", "isp_crop_template", "isp_dpc_template",
    "isp_blc_template", "isp_oecf_template", "isp_dg_template",
    "isp_lsc_template", "isp_bnr_template", "isp_wb_template",
    "isp_awb_stats_template", "isp_demosaic_template", "isp_ccm_template",
    "isp_gamma_template", "isp_ae_stats_template", "isp_csc_template",
    "isp_ldci_template", "isp_sharpen_template", "isp_nr2d_template",
    "isp_scale_template", "isp_yuv_template", "isp_axi_out_template",
    "isp_apb_regs_template",
]

TemplateRegistry.register("isp_ae_stats", isp_ae_stats_template)
TemplateRegistry.register("isp_apb_regs", isp_apb_regs_template)
TemplateRegistry.register("isp_awb_stats", isp_awb_stats_template)
TemplateRegistry.register("isp_axi_in", isp_axi_in_template)
TemplateRegistry.register("isp_axi_out", isp_axi_out_template)
TemplateRegistry.register("isp_blc", isp_blc_template)
TemplateRegistry.register("isp_bnr", isp_bnr_template)
TemplateRegistry.register("isp_ccm", isp_ccm_template)
TemplateRegistry.register("isp_crop", isp_crop_template)
TemplateRegistry.register("isp_csc", isp_csc_template)
TemplateRegistry.register("isp_demosaic", isp_demosaic_template)
TemplateRegistry.register("isp_dg", isp_dg_template)
TemplateRegistry.register("isp_dpc", isp_dpc_template)
TemplateRegistry.register("isp_gamma", isp_gamma_template)
TemplateRegistry.register("isp_ldci", isp_ldci_template)
TemplateRegistry.register("isp_lsc", isp_lsc_template)
TemplateRegistry.register("isp_nr2d", isp_nr2d_template)
TemplateRegistry.register("isp_oecf", isp_oecf_template)
TemplateRegistry.register("isp_scale", isp_scale_template)
TemplateRegistry.register("isp_sharpen", isp_sharpen_template)
TemplateRegistry.register("isp_wb", isp_wb_template)
TemplateRegistry.register("isp_yuv", isp_yuv_template)
__all__ = [
