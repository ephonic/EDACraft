"""
skills.codec.video.behaviors — Video Codec Behavior Templates

Domain-specific behavior templates for xk265 H.265/HEVC encoder pipeline stages.
Registered into TemplateRegistry at import time.

Pipeline stages:
  - enc_ctrl:       Top-level FSM controller (CTU sequencing)
  - prei_processor: Pre-intra estimation (gradient, mode decision, rate control)
  - posi_processor: Intra prediction search (SATD + partition)
  - ime_processor:  Integer motion estimation (SAD array + partition)
  - fme_processor:  Fractional motion estimation (1/4-pel refinement)
  - rec_processor:  Reconstruction (intra + MC + TQ)
  - dbsao_processor: Deblocking + SAO
  - cabac_processor: CABAC entropy coding
  - fetch_processor: Memory interface / pixel buffer
"""
from __future__ import annotations

from typing import Any, Callable

from rtlgen.arch_def import CycleContext
from rtlgen.behaviors import TemplateRegistry


def enc_ctrl_template(
    num_pipeline_stages: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Encoder top-level controller behavior.

    Manages CTU raster-scan sequencing through the pipeline:
    PREI → POSI → IME → FME → REC → DBSAO → CABAC → FETCH
    """
    stage_names = ["PREI", "POSI", "IME", "FME", "REC", "DB", "CABAC", "FETCH"]

    def behavior(ctx: CycleContext):
        sys_start = ctx.get_input("sys_start_i", 0)
        done_signals = {
            "PREI": ctx.get_input("prei_done_i", 0),
            "POSI": ctx.get_input("posi_done_i", 0),
            "IME": ctx.get_input("ime_done_i", 0),
            "FME": ctx.get_input("fme_done_i", 0),
            "REC": ctx.get_input("rec_done_i", 0),
            "DB": ctx.get_input("db_done_i", 0),
            "CABAC": ctx.get_input("cabac_done_i", 0),
            "FETCH": ctx.get_input("fetch_done_i", 0),
        }

        state = ctx.get_state("state", 0)  # 0=IDLE, 1..8=pipeline stages
        ctu_x = ctx.get_state("ctu_x", 0)
        ctu_y = ctx.get_state("ctu_y", 0)
        total_x = ctx.get_input("sys_total_x_i", 1)
        total_y = ctx.get_input("sys_total_y_i", 1)

        if state == 0:  # IDLE
            if sys_start:
                state = 1
                ctu_x = 0
                ctu_y = 0
        else:  # In pipeline
            current_stage = stage_names[state - 1] if state - 1 < len(stage_names) else "FETCH"
            if done_signals.get(current_stage, 0):
                if state < num_pipeline_stages:
                    state = state + 1
                else:
                    # Last stage done → advance CTU
                    if ctu_x + 1 < total_x:
                        ctu_x = ctu_x + 1
                        state = 1
                    elif ctu_y + 1 < total_y:
                        ctu_x = 0
                        ctu_y = ctu_y + 1
                        state = 1
                    else:
                        state = 0  # Frame done → IDLE

        ctx.set_state("state", state)
        ctx.set_state("ctu_x", ctu_x)
        ctx.set_state("ctu_y", ctu_y)

        # Output start signals
        for i, name in enumerate(stage_names):
            ctx.set_output(f"{name.lower()}_start_o", 1 if state == i + 1 else 0)

        ctx.set_output("ctu_x_cur_o", ctu_x)
        ctx.set_output("ctu_y_cur_o", ctu_y)
        ctx.set_output("sys_done_o", 1 if state == 0 and ctx.get_state("was_running", 0) else 0)
        ctx.set_state("was_running", 1 if state != 0 else 0)

    return behavior


def prei_template(
    lcu_size: int = 64,
    pixel_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Pre-intra estimation behavior.

    Computes gradient (GxGy) for edge detection, performs mode decision
    and rate control QP adjustment.
    """
    pixels_per_ctu = lcu_size * lcu_size
    cycles_per_ctu = pixels_per_ctu // 32  # 32 pixels/cycle throughput

    def behavior(ctx: CycleContext):
        start = ctx.get_input("start_i", 0)
        active = ctx.get_state("active", 0)
        cnt = ctx.get_state("cnt", 0)

        if start and not active:
            active = 1
            cnt = 0
        elif active:
            cnt = cnt + 1
            if cnt >= cycles_per_ctu - 1:
                active = 0
                cnt = 0

        ctx.set_state("active", active)
        ctx.set_state("cnt", cnt)
        ctx.set_output("done_o", 1 if (active and cnt >= cycles_per_ctu - 1) else 0)
        ctx.set_output("md_ren_o", active)

    return behavior


def posi_template(
    lcu_size: int = 64,
    cu_depth: int = 3,
    num_modes: int = 35,
    cost_width: int = 20,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Intra prediction search behavior.

    SATD-based cost computation for all 35 intra prediction modes
    across 4 block sizes (64x64, 32x32, 16x16, 8x8).
    """
    # Total blocks per CTU at all depths
    total_blocks = sum(4**d for d in range(cu_depth + 1))  # 1+4+16+64=85
    cycles_per_block = num_modes * 2  # 2 cycles per mode

    def behavior(ctx: CycleContext):
        start = ctx.get_input("start_i", 0)
        active = ctx.get_state("active", 0)
        block_cnt = ctx.get_state("block_cnt", 0)
        mode_cnt = ctx.get_state("mode_cnt", 0)
        best_cost = ctx.get_state("best_cost", (1 << cost_width) - 1)

        if start and not active:
            active = 1
            block_cnt = 0
            mode_cnt = 0
            best_cost = (1 << cost_width) - 1

        if active:
            mode_cnt = mode_cnt + 1
            satd_cost = ctx.get_input("satd_cost_i", 0)
            if satd_cost < best_cost:
                best_cost = satd_cost
                ctx.set_state("best_mode", mode_cnt)

            if mode_cnt >= num_modes:
                mode_cnt = 0
                block_cnt = block_cnt + 1
                if block_cnt >= total_blocks:
                    active = 0

        ctx.set_state("active", active)
        ctx.set_state("block_cnt", block_cnt)
        ctx.set_state("mode_cnt", mode_cnt)
        ctx.set_state("best_cost", best_cost)
        ctx.set_output("done_o", 1 if not active and ctx.get_state("was_active", 0) else 0)
        ctx.set_state("was_active", active)
        ctx.set_output("cost_o", best_cost)

    return behavior


def ime_template(
    lcu_size: int = 64,
    search_range: int = 64,
    pixel_width: int = 4,
    cost_width: int = 28,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Integer motion estimation behavior.

    Multi-scale SAD computation (4x4, 8x8, 16x16, 32x32) with
    search pattern traversal and partition decision.
    """
    total_search_points = search_range * search_range

    def behavior(ctx: CycleContext):
        start = ctx.get_input("start_i", 0)
        phase = ctx.get_state("phase", 0)  # 0=IDLE, 1=ADR, 2=SAD, 3=DEC, 4=DMP
        point_cnt = ctx.get_state("point_cnt", 0)
        best_sad = ctx.get_state("best_sad", (1 << cost_width) - 1)
        best_mv_x = ctx.get_state("best_mv_x", 0)
        best_mv_y = ctx.get_state("best_mv_y", 0)

        if start and phase == 0:
            phase = 1  # ADR (addressing)

        if phase == 1:  # Addressing
            phase = 2
            point_cnt = 0
            best_sad = (1 << cost_width) - 1

        elif phase == 2:  # SAD computation
            sad_val = ctx.get_input("sad_val_i", 0)
            mv_x = ctx.get_input("mv_x_i", 0)
            mv_y = ctx.get_input("mv_y_i", 0)
            if sad_val > 0 and sad_val < best_sad:
                best_sad = sad_val
                best_mv_x = mv_x
                best_mv_y = mv_y

            point_cnt = point_cnt + 1
            if point_cnt >= total_search_points:
                phase = 3

        elif phase == 3:  # Partition decision
            phase = 4

        elif phase == 4:  # MV dump
            phase = 0

        ctx.set_state("phase", phase)
        ctx.set_state("point_cnt", point_cnt)
        ctx.set_state("best_sad", best_sad)
        ctx.set_state("best_mv_x", best_mv_x)
        ctx.set_state("best_mv_y", best_mv_y)
        ctx.set_output("done_o", 1 if phase == 0 and ctx.get_state("was_active", 0) else 0)
        ctx.set_state("was_active", 1 if phase != 0 else 0)
        ctx.set_output("mv_wr_ena_o", 1 if phase == 4 else 0)

    return behavior


def fme_template(
    lcu_size: int = 64,
    cost_width: int = 20,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Fractional motion estimation behavior.

    1/4-pel interpolation and refinement around integer MV positions.
    """
    refinement_points = 25  # 5x5 around integer MV

    def behavior(ctx: CycleContext):
        start = ctx.get_input("start_i", 0)
        phase = ctx.get_state("phase", 0)  # 0=IDLE, 1=interp, 2=refine, 3=done
        point_cnt = ctx.get_state("point_cnt", 0)
        best_cost = ctx.get_state("best_cost", (1 << cost_width) - 1)

        if start and phase == 0:
            phase = 1

        if phase == 1:  # Interpolation
            phase = 2
            point_cnt = 0

        elif phase == 2:  # Refinement
            fme_cost = ctx.get_input("fme_cost_i", 0)
            if fme_cost > 0 and fme_cost < best_cost:
                best_cost = fme_cost

            point_cnt = point_cnt + 1
            if point_cnt >= refinement_points:
                phase = 3

        elif phase == 3:
            phase = 0

        ctx.set_state("phase", phase)
        ctx.set_state("point_cnt", point_cnt)
        ctx.set_state("best_cost", best_cost)
        ctx.set_output("done_o", 1 if phase == 0 and ctx.get_state("was_active", 0) else 0)
        ctx.set_state("was_active", 1 if phase != 0 else 0)

    return behavior


def rec_template(
    lcu_size: int = 64,
    coeff_width: int = 16,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Reconstruction behavior.

    Intra prediction generation, motion compensation, transform/quantization,
    and inverse transform for reconstructed pixel generation.
    """
    pixels_per_ctu = lcu_size * lcu_size

    def behavior(ctx: CycleContext):
        start = ctx.get_input("start_i", 0)
        phase = ctx.get_state("phase", 0)  # 0=IDLE, 1=intra, 2=mc, 3=tq, 4=done
        pixel_cnt = ctx.get_state("pixel_cnt", 0)

        if start and phase == 0:
            ctx.set_state("type_i", ctx.get_input("type_i", 0))
            phase = 1

        if phase == 1:  # Intra prediction
            pixel_cnt = pixel_cnt + 1
            if pixel_cnt >= pixels_per_ctu:
                pixel_cnt = 0
                if ctx.get_state("type_i", 0) == 0:  # Intra
                    phase = 3  # Skip MC, go to TQ
                else:
                    phase = 2  # Inter → MC

        elif phase == 2:  # Motion compensation
            pixel_cnt = pixel_cnt + 1
            if pixel_cnt >= pixels_per_ctu:
                phase = 3

        elif phase == 3:  # Transform + Quantization
            pixel_cnt = pixel_cnt + 1
            if pixel_cnt >= pixels_per_ctu:
                phase = 4

        elif phase == 4:
            phase = 0

        ctx.set_state("phase", phase)
        ctx.set_state("pixel_cnt", pixel_cnt)
        ctx.set_output("done_o", 1 if phase == 0 and ctx.get_state("was_active", 0) else 0)
        ctx.set_state("was_active", 1 if phase != 0 else 0)

    return behavior


def dbsao_template(
    lcu_size: int = 64,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Deblocking filter + SAO behavior.

    Adaptive deblocking filter on PU/TU boundaries, followed by
    Sample Adaptive Offset (Edge Offset + Band Offset) processing.
    """
    pixels_per_ctu = lcu_size * lcu_size

    def behavior(ctx: CycleContext):
        start = ctx.get_input("sys_start_i", 0)
        phase = ctx.get_state("phase", 0)  # 0=IDLE, 1=db_edge, 2=db_pu, 3=sao, 4=done
        pixel_cnt = ctx.get_state("pixel_cnt", 0)
        db_en = ctx.get_input("sys_db_ena_i", 1)
        sao_en = ctx.get_input("sys_sao_ena_i", 1)

        if start and phase == 0:
            phase = 1 if db_en else (3 if sao_en else 4)

        if phase == 1:  # Deblock vertical edges
            pixel_cnt = pixel_cnt + 1
            if pixel_cnt >= pixels_per_ctu:
                phase = 2 if db_en else (3 if sao_en else 4)
                pixel_cnt = 0

        elif phase == 2:  # Deblock horizontal edges
            pixel_cnt = pixel_cnt + 1
            if pixel_cnt >= pixels_per_ctu:
                phase = 3 if sao_en else 4
                pixel_cnt = 0

        elif phase == 3:  # SAO
            pixel_cnt = pixel_cnt + 1
            if pixel_cnt >= pixels_per_ctu:
                phase = 4
                pixel_cnt = 0

        elif phase == 4:
            phase = 0

        ctx.set_state("phase", phase)
        ctx.set_state("pixel_cnt", pixel_cnt)
        ctx.set_output("sys_done_o", 1 if phase == 0 and ctx.get_state("was_active", 0) else 0)
        ctx.set_state("was_active", 1 if phase != 0 else 0)

    return behavior


def cabac_template(
    lcu_size: int = 64,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """CABAC entropy coding behavior.

    Context-adaptive binary arithmetic coding: binarization,
    context modeling, and arithmetic encoding of syntax elements.
    """
    num_4x4 = (lcu_size // 4) * (lcu_size // 4)  # 256 for 64x64

    def behavior(ctx: CycleContext):
        start = ctx.get_input("sys_start_i", 0)
        active = ctx.get_state("active", 0)
        blk_cnt = ctx.get_state("blk_cnt", 0)

        if start and not active:
            active = 1
            blk_cnt = 0

        if active:
            blk_cnt = blk_cnt + 1
            # Generate bitstream output
            ctx.set_output("bs_val_o", 1)
            ctx.set_output("bs_data_o", blk_cnt & 0xFF)

            if blk_cnt >= num_4x4:
                active = 0
                ctx.set_output("cabac_done_o", 1)
                ctx.set_output("bs_val_o", 0)

        ctx.set_state("active", active)
        ctx.set_state("blk_cnt", blk_cnt)

    return behavior


def fetch_template(
    lcu_size: int = 64,
    pixel_width: int = 8,
    **kwargs,
) -> Callable[[CycleContext], None]:
    """Memory fetch behavior.

    Manages pixel data movement between external memory and on-chip buffers:
    current frame pixels, reference frame pixels, reconstructed pixels.
    """
    pixels_per_ctu = lcu_size * lcu_size
    burst_size = 32  # pixels per burst

    def behavior(ctx: CycleContext):
        start = ctx.get_input("sysif_start_i", 0)
        active = ctx.get_state("active", 0)
        burst_cnt = ctx.get_state("burst_cnt", 0)
        total_bursts = (pixels_per_ctu + burst_size - 1) // burst_size

        if start and not active:
            active = 1
            burst_cnt = 0

        if active:
            burst_cnt = burst_cnt + 1
            if burst_cnt >= total_bursts:
                active = 0
                ctx.set_output("sysif_done_o", 1)

        ctx.set_state("active", active)
        ctx.set_state("burst_cnt", burst_cnt)
        ctx.set_output("extif_start_o", active)

    return behavior


# Register codec templates
TemplateRegistry.register("enc_ctrl", enc_ctrl_template)
TemplateRegistry.register("prei_processor", prei_template)
TemplateRegistry.register("posi_processor", posi_template)
TemplateRegistry.register("ime_processor", ime_template)
TemplateRegistry.register("fme_processor", fme_template)
TemplateRegistry.register("rec_processor", rec_template)
TemplateRegistry.register("dbsao_processor", dbsao_template)
TemplateRegistry.register("cabac_processor", cabac_template)
TemplateRegistry.register("fetch_processor", fetch_template)

__all__ = [
    "enc_ctrl_template",
    "prei_template",
    "posi_template",
    "ime_template",
    "fme_template",
    "rec_template",
    "dbsao_template",
    "cabac_template",
    "fetch_template",
]
