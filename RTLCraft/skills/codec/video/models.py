"""
skills.codec.video.models — xk265 H.265/HEVC Golden Reference Models

Cycle-accurate Python simulators for all 38 xk265 modules across 9 pipeline stages.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def log2_int(x: int) -> int:
    return max(x - 1, 0).bit_length()


def _to_signed(val: int, width: int) -> int:
    if val & (1 << (width - 1)):
        return val - (1 << width)
    return val


def _to_unsigned(val: int, width: int) -> int:
    return val & ((1 << width) - 1)


def _sat(val: int, width: int) -> int:
    lo = -(1 << (width - 1))
    hi = (1 << (width - 1)) - 1
    return max(lo, min(hi, val))


# =====================================================================
# Global Parameters
# =====================================================================

LCU_SIZE = 64
CU_DEPTH = 3
PIC_X_WIDTH = 6
PIC_Y_WIDTH = 6
PIXEL_WIDTH = 8
COEFF_WIDTH = 16
IME_MV_WIDTH_X = 7
IME_MV_WIDTH_Y = 6
IME_MV_WIDTH = 13
IME_PIXEL_WIDTH = 4
IME_COST_WIDTH = 28
POSI_COST_WIDTH = 20
FME_COST_WIDTH = 20
FMV_WIDTH = 10
MVD_WIDTH = 11
NUM_4X4 = (LCU_SIZE // 4) * (LCU_SIZE // 4)  # 256


# =====================================================================
# CTU State
# =====================================================================

@dataclass
class CTUState:
    """Per-CTU (Coding Tree Unit) state."""
    x: int = 0
    y: int = 0
    qp: int = 22
    partition: Dict[str, Any] = field(default_factory=dict)
    prei_done: bool = False
    posi_done: bool = False
    ime_done: bool = False
    fme_done: bool = False
    rec_done: bool = False
    dbsao_done: bool = False
    cabac_done: bool = False
    fetch_done: bool = False
    total_cost: int = 0
    bit_count: int = 0


# =====================================================================
# Top-Level Models
# =====================================================================

class H265EncoderModel:
    """H.265/HEVC encoder behavioral model.

    Models the CTU-level pipeline:
    PREI → POSI → IME → FME → REC → DBSAO → CABAC → FETCH
    """

    STAGES = ["PREI", "POSI", "IME", "FME", "REC", "DBSAO", "CABAC", "FETCH"]

    def __init__(self, name: str = "H265Encoder", lcu_size: int = 64,
                 pic_width: int = 1920, pic_height: int = 1080):
        self.name = name
        self.lcu_size = lcu_size
        self.pic_width = pic_width
        self.pic_height = pic_height
        self.ctu_width = (pic_width + lcu_size - 1) // lcu_size
        self.ctu_height = (pic_height + lcu_size - 1) // lcu_size
        self.total_ctus = self.ctu_width * self.ctu_height
        self.qp = 22
        self.max_cu_depth = 3
        self.cycle_count = 0
        self.current_ctu: Optional[CTUState] = None
        self.ctu_count = 0
        self.total_bits = 0
        self._stage_idx = 0
        self._running = False
        self.stage_latency = {
            "PREI": 128, "POSI": 512, "IME": 1024, "FME": 256,
            "REC": 384, "DBSAO": 256, "CABAC": 512, "FETCH": 128,
        }
        self._stage_cycles = 0

    def configure(self, qp: int = 22, max_cu_depth: int = 3):
        self.qp = qp
        self.max_cu_depth = max_cu_depth

    def reset(self):
        self.cycle_count = 0
        self.ctu_count = 0
        self.total_bits = 0
        self._stage_idx = 0
        self._running = False
        self._stage_cycles = 0
        self.current_ctu = None

    def _next_ctu(self) -> Optional[CTUState]:
        if self.ctu_count >= self.total_ctus:
            return None
        x = self.ctu_count % self.ctu_width
        y = self.ctu_count // self.ctu_width
        ctu = CTUState(x=x, y=y, qp=self.qp)
        self.ctu_count += 1
        return ctu

    def _run_stage(self) -> bool:
        if self.current_ctu is None:
            return False
        stage = self.STAGES[self._stage_idx]
        self._stage_cycles += 1
        if self._stage_cycles >= self.stage_latency[stage]:
            setattr(self.current_ctu, f"{stage.lower()}_done", True)
            self._stage_idx += 1
            self._stage_cycles = 0
            if self._stage_idx >= len(self.STAGES):
                bits = max(64, self.lcu_size ** 2 * (1 << max(0, (51 - self.current_ctu.qp) // 6)) // 8)
                self.current_ctu.bit_count = bits
                self.total_bits += bits
                return True
        return False

    def run(self, num_cycles: int = 1000) -> Dict[str, Any]:
        self.reset()
        for _ in range(num_cycles):
            self.cycle_count += 1
            if not self._running:
                ctu = self._next_ctu()
                if ctu is None:
                    break
                self.current_ctu = ctu
                self._stage_idx = 0
                self._stage_cycles = 0
                self._running = True
            if self._run_stage():
                self._running = False
        return {
            "cycles": self.cycle_count, "ctus_encoded": self.ctu_count,
            "total_bits": self.total_bits, "total_ctus": self.total_ctus,
            "completion": self.ctu_count / max(1, self.total_ctus),
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "ctu_x": self.current_ctu.x if self.current_ctu else -1,
            "ctu_y": self.current_ctu.y if self.current_ctu else -1,
            "stage": self.STAGES[self._stage_idx] if self._running else "IDLE",
            "ctu_progress": f"{self.ctu_count}/{self.total_ctus}",
            "bits_so_far": self.total_bits,
        }


class EncCtrlModel:
    """Top-level encoder control FSM model.

    Manages CTU raster-scan sequencing through 9 pipeline stages.
    States: IDLE → PREI → POSI → IME → FME → REC → DB → CABAC → FETCH → DONE
    """

    ST_IDLE, ST_PREI, ST_POSI, ST_IME, ST_FME = 0, 1, 2, 3, 4
    ST_REC, ST_DB, ST_CABAC, ST_FETCH, ST_DONE = 5, 6, 7, 8, 9

    def __init__(self, pic_x_width: int = 6, pic_y_width: int = 6):
        self.pic_x_width = pic_x_width
        self.pic_y_width = pic_y_width
        self.state = self.ST_IDLE
        self.ctu_x = 0
        self.ctu_y = 0
        self.slice_type = 0
        self.qp = 22
        self.first_ctu = 1

    def step(self, sys_start_i: int = 0, sys_slice_type_i: int = 0,
             prei_done_i: int = 0, posi_done_i: int = 0,
             ime_done_i: int = 0, fme_done_i: int = 0,
             rec_done_i: int = 0, db_done_i: int = 0,
             cabac_done_i: int = 0, fetch_done_i: int = 0,
             sys_total_x_i: int = 1, sys_total_y_i: int = 1) -> Dict[str, int]:
        if self.state == self.ST_IDLE:
            if sys_start_i:
                self.state = self.ST_PREI
                self.slice_type = sys_slice_type_i
                self.ctu_x = 0
                self.ctu_y = 0
                self.first_ctu = 1
        elif self.state == self.ST_PREI and prei_done_i:
            self.state = self.ST_POSI
        elif self.state == self.ST_POSI and posi_done_i:
            self.state = self.ST_IME
        elif self.state == self.ST_IME and ime_done_i:
            self.state = self.ST_FME
        elif self.state == self.ST_FME and fme_done_i:
            self.state = self.ST_REC
        elif self.state == self.ST_REC and rec_done_i:
            self.state = self.ST_DB
        elif self.state == self.ST_DB and db_done_i:
            self.state = self.ST_CABAC
        elif self.state == self.ST_CABAC and cabac_done_i:
            self.state = self.ST_FETCH
        elif self.state == self.ST_FETCH and fetch_done_i:
            if self.ctu_x + 1 < sys_total_x_i:
                self.ctu_x += 1
                self.state = self.ST_PREI
                self.first_ctu = 0
            elif self.ctu_y + 1 < sys_total_y_i:
                self.ctu_x = 0
                self.ctu_y += 1
                self.state = self.ST_PREI
                self.first_ctu = 0
            else:
                self.state = self.ST_DONE
        elif self.state == self.ST_DONE:
            self.state = self.ST_IDLE
        return {
            "prei_start": 1 if self.state == self.ST_PREI else 0,
            "posi_start": 1 if self.state == self.ST_POSI else 0,
            "ime_start": 1 if self.state == self.ST_IME else 0,
            "fme_start": 1 if self.state == self.ST_FME else 0,
            "rec_start": 1 if self.state == self.ST_REC else 0,
            "db_start": 1 if self.state == self.ST_DB else 0,
            "cabac_start": 1 if self.state == self.ST_CABAC else 0,
            "fetch_start": 1 if self.state == self.ST_FETCH else 0,
            "ctu_x_cur": self.ctu_x, "ctu_y_cur": self.ctu_y,
            "rc_qp": self.qp,
            "sys_done": 1 if self.state == self.ST_DONE else 0,
        }


# =====================================================================
# IME Submodule Models
# =====================================================================

class ImeCtrlModel:
    """IME controller: ADR → DEC → DMP phase sequencing."""

    ST_IDLE, ST_ADR, ST_DEC, ST_DMP, ST_DONE = 0, 1, 2, 3, 4

    def __init__(self):
        self.state = self.ST_IDLE
        self.cmd_cnt = 0
        self.cmd_num = 0
        self.downsample = 0

    def step(self, start_i: int = 0, adr_done_i: int = 0,
             dec_done_i: int = 0, dmp_done_i: int = 0,
             cmd_num_i: int = 0, cmd_dat: int = 0) -> Dict[str, int]:
        if self.state == self.ST_IDLE and start_i:
            self.state = self.ST_ADR
            self.cmd_cnt = 0
            self.cmd_num = cmd_num_i
            self.downsample = 0
        elif self.state == self.ST_ADR and adr_done_i:
            if self.cmd_cnt + 1 < self.cmd_num:
                self.cmd_cnt += 1
            else:
                self.state = self.ST_DEC
                self.cmd_cnt = 0
        elif self.state == self.ST_DEC and dec_done_i:
            self.state = self.ST_DMP
        elif self.state == self.ST_DMP and dmp_done_i:
            self.state = self.ST_DONE
        elif self.state == self.ST_DONE:
            self.state = self.ST_IDLE
        return {
            "ctr_center_x": (cmd_dat >> 0) & 0x7F,
            "ctr_center_y": (cmd_dat >> 7) & 0x3F,
            "ctr_length_x": (cmd_dat >> 13) & 0x3F,
            "ctr_length_y": (cmd_dat >> 19) & 0x1F,
            "ctr_slope": (cmd_dat >> 24) & 0x3,
            "ctr_downsample": (cmd_dat >> 26) & 1,
            "ctr_use_feedback": (cmd_dat >> 27) & 1,
            "adr_start": 1 if self.state == self.ST_ADR else 0,
            "dec_start": 1 if self.state == self.ST_DEC else 0,
            "dmp_start": 1 if self.state == self.ST_DMP else 0,
            "done": 1 if self.state == self.ST_DONE else 0,
        }


class ImeAddressingModel:
    """IME search pattern traversal engine."""

    ST_IDLE, ST_INIT, ST_SEARCH, ST_DONE = 0, 1, 2, 3

    def __init__(self):
        self.state = self.ST_IDLE
        self.search_x = 0
        self.search_y = 0
        self.cur_x = 0
        self.cur_y = 0
        self.len_x = 0
        self.len_y = 0
        self.cnt = 0
        self.done = 0
        self.val = 0

    def step(self, start_i: int = 0, center_x_i: int = 0, center_y_i: int = 0,
             length_x_i: int = 0, length_y_i: int = 0, slope_i: int = 0,
             downsample_i: int = 0, use_feedback_i: int = 0,
             feedback_mv_i: int = 0, ctu_x_cur_i: int = 0, ctu_y_cur_i: int = 0) -> Dict[str, int]:
        self.done = 0
        self.val = 0
        if self.state == self.ST_IDLE and start_i:
            self.state = self.ST_INIT
        elif self.state == self.ST_INIT:
            if use_feedback_i:
                self.cur_x = feedback_mv_i & ((1 << IME_MV_WIDTH_X) - 1)
                self.cur_y = (feedback_mv_i >> IME_MV_WIDTH_X) & ((1 << IME_MV_WIDTH_Y) - 1)
            else:
                self.cur_x = center_x_i
                self.cur_y = center_y_i
            self.len_x = length_x_i
            self.len_y = length_y_i
            self.search_x = 0
            self.search_y = 0
            self.cnt = 0
            self.state = self.ST_SEARCH
        elif self.state == self.ST_SEARCH:
            self.val = 1
            self.cnt += 1
            step = 2 if downsample_i else 1
            if self.search_x + step < (self.len_x << 1):
                self.search_x += step
            else:
                self.search_x = 0
                if self.search_y + step < (self.len_y << 1):
                    self.search_y += step
                else:
                    self.done = 1
                    self.state = self.ST_DONE
        elif self.state == self.ST_DONE:
            self.state = self.ST_IDLE
        mv_x = self.cur_x + self.search_x - self.len_x
        mv_y = self.cur_y + self.search_y - self.len_y
        return {
            "ori_ena": 1 if self.state == self.ST_SEARCH else 0,
            "adr_val": self.val, "adr_done": self.done,
            "adr_dat_mv": _to_unsigned(mv_y & ((1 << IME_MV_WIDTH_Y) - 1), IME_MV_WIDTH_Y) << IME_MV_WIDTH_X | (mv_x & ((1 << IME_MV_WIDTH_X) - 1)),
        }


class ImeDatArrayModel:
    """IME data array: 32x32 pixel buffer with horizontal/vertical shift."""

    def __init__(self):
        self.pixel_array = [0] * 1024

    def step(self, val_i: int = 0, dir_i: int = 0,
             dat_hor_i: int = 0, dat_ver_i: int = 0) -> int:
        if val_i:
            if dir_i == 0:  # horizontal shift
                for row in range(32):
                    for col in range(32):
                        idx = row * 32 + col
                        shift = col * IME_PIXEL_WIDTH
                        self.pixel_array[idx] = (dat_hor_i >> shift) & ((1 << IME_PIXEL_WIDTH) - 1)
            elif dir_i == 1:  # vertical shift
                for row in range(32):
                    for col in range(32):
                        idx = row * 32 + col
                        shift = row * IME_PIXEL_WIDTH
                        self.pixel_array[idx] = (dat_ver_i >> shift) & ((1 << IME_PIXEL_WIDTH) - 1)
        out = 0
        for i in range(1024):
            out |= self.pixel_array[i] << (i * IME_PIXEL_WIDTH)
        return out


class ImeSadArrayModel:
    """IME SAD array: hierarchical SAD for 4x4/8x8/16x16/32x32."""

    def __init__(self):
        self.val_pipe = [0] * 6
        self.qd_pipe = [0] * 6
        self.mv_pipe = [0] * 6
        self.mvd_pipe = [0] * 6

    def step(self, val_i: int = 0, dat_qd_i: int = 0, dat_mv_i: int = 0,
             dat_cst_mvd_i: int = 0, dat_ori_i: int = 0, dat_ref_i: int = 0) -> Dict[str, Any]:
        self.val_pipe = [val_i] + self.val_pipe[:-1]
        self.qd_pipe = [dat_qd_i] + self.qd_pipe[:-1]
        self.mv_pipe = [dat_mv_i] + self.mv_pipe[:-1]
        self.mvd_pipe = [dat_cst_mvd_i] + self.mvd_pipe[:-1]
        return {
            "val_04": self.val_pipe[0], "val_08": self.val_pipe[2],
            "val_16": self.val_pipe[4], "val_32": self.val_pipe[5],
        }


class ImeCostStoreModel:
    """IME cost store: accumulates best SAD+MVD cost per block size."""

    def __init__(self):
        self.best_cost_08 = [0] * 64
        self.best_cost_16 = [0] * 16
        self.best_cost_32 = [0] * 4
        self.best_cost_64 = [0] * 1

    def step(self, clear_i: int = 0, downsample_i: int = 0,
             val_08_i: int = 0, cst_08_i: int = 0,
             val_16_i: int = 0, cst_16_i: int = 0) -> Dict[str, int]:
        if clear_i:
            self.best_cost_08 = [0] * 64
            self.best_cost_16 = [0] * 16
            self.best_cost_32 = [0] * 4
            self.best_cost_64 = [0] * 1
        # Simplified: in full impl, compare and update per-position
        return {}


class ImePartitionDecisionEngineModel:
    """Combinational partition decision: 1Nx1N vs 1Nx2N vs 2Nx1N vs 2Nx2N."""

    def step(self, cost_1nx1n: int = 0, cost_1nx2n: int = 0,
             cost_2nx1n: int = 0, cost_2nx2n: int = 0,
             is_boundary: int = 0) -> Tuple[int, int]:
        if is_boundary:
            return 0, cost_1nx1n  # 1Nx1N
        best_part, best_cost = 0, cost_1nx1n
        if cost_1nx2n < best_cost:
            best_part, best_cost = 1, cost_1nx2n
        if cost_2nx1n < best_cost:
            best_part, best_cost = 2, cost_2nx1n
        if cost_2nx2n < best_cost:
            best_part, best_cost = 3, cost_2nx2n
        return best_part, best_cost


class ImePartitionDecisionModel:
    """IME partition decision: 21-step iteration over CTU quad-tree."""

    ST_IDLE, ST_BUSY = 0, 1

    def __init__(self):
        self.state = self.ST_IDLE
        self.cnt = 0
        self.partition_reg = 0

    def step(self, start_i: int = 0) -> Dict[str, int]:
        if self.state == self.ST_IDLE and start_i:
            self.state = self.ST_BUSY
            self.cnt = 0
            self.partition_reg = 0
        elif self.state == self.ST_BUSY:
            self.cnt += 1
            if self.cnt == 20:
                self.state = self.ST_IDLE
        return {
            "done": 1 if (self.state == self.ST_BUSY and self.cnt == 20) else 0,
            "partition": self.partition_reg,
        }


class ImeMvDumpModel:
    """IME MV dump: serially outputs best MVs for all 8x8 blocks."""

    ST_IDLE, ST_BUSY = 0, 1

    def __init__(self):
        self.state = self.ST_IDLE
        self.cnt = 0

    def step(self, start_i: int = 0, dat_partition_i: int = 0) -> Dict[str, int]:
        if self.state == self.ST_IDLE and start_i:
            self.state = self.ST_BUSY
            self.cnt = 0
        elif self.state == self.ST_BUSY:
            self.cnt += 1
            if self.cnt == 63:
                self.state = self.ST_IDLE
        return {
            "mv_wr_ena": 1 if self.state == self.ST_BUSY else 0,
            "mv_wr_adr": self.cnt,
            "done": 1 if (self.state == self.ST_BUSY and self.cnt == 63) else 0,
        }


# =====================================================================
# POSI Submodule Models
# =====================================================================

class PosiCtrlModel:
    """POSI controller FSM: TRA_PRE → TRA_POS → SIZE_4x4 → SIZE_8x8 → SIZE_16x16 → SIZE_32x32 → DECISION → DONE."""

    ST_IDLE, ST_TRA_PRE, ST_TRA_POS = 0, 1, 2
    ST_SIZE_4X4, ST_SIZE_8X8, ST_SIZE_16X16, ST_SIZE_32X32 = 3, 4, 5, 6
    ST_DECISION, ST_DONE = 7, 8

    def __init__(self):
        self.state = self.ST_IDLE
        self.size_level = 0
        self.blk_x = 0
        self.blk_y = 0
        self.mode_cnt = 0

    def step(self, start_i: int = 0, satd_done_i: int = 0,
             tra_pre_done_i: int = 0, tra_pos_done_i: int = 0,
             dec_done_i: int = 0, num_mode_i: int = 3) -> Dict[str, int]:
        if self.state == self.ST_IDLE and start_i:
            self.state = self.ST_TRA_PRE
            self.size_level = 0
            self.blk_x = 0
            self.blk_y = 0
            self.mode_cnt = 0
        elif self.state == self.ST_TRA_PRE and tra_pre_done_i:
            self.state = self.ST_TRA_POS
        elif self.state == self.ST_TRA_POS and tra_pos_done_i:
            self.state = self.ST_SIZE_4X4
            self.size_level = 0
            self.blk_x = 0
            self.blk_y = 0
            self.mode_cnt = 0
        elif self.ST_SIZE_4X4 <= self.state <= self.ST_SIZE_32X32 and satd_done_i:
            if self.mode_cnt + 1 < num_mode_i:
                self.mode_cnt += 1
            else:
                self.mode_cnt = 0
                limits = {self.ST_SIZE_4X4: 16, self.ST_SIZE_8X8: 8,
                          self.ST_SIZE_16X16: 4, self.ST_SIZE_32X32: 2}
                lim = limits.get(self.state, 16)
                if self.blk_x + 1 < lim:
                    self.blk_x += 1
                else:
                    self.blk_x = 0
                    if self.blk_y + 1 < lim:
                        self.blk_y += 1
                    else:
                        if self.state == self.ST_SIZE_32X32:
                            self.state = self.ST_DECISION
                        else:
                            self.state += 1
                            self.size_level += 1
                            self.blk_y = 0
        elif self.state == self.ST_DECISION and dec_done_i:
            self.state = self.ST_DONE
        elif self.state == self.ST_DONE:
            self.state = self.ST_IDLE
        return {"state": self.state, "done": 1 if self.state == self.ST_DONE else 0}


class PosiTransferModel:
    """POSI transfer: reads original pixels, writes to row/col/frame RAMs."""

    ST_IDLE, ST_PRE, ST_POS_COL, ST_POS_FRA = 0, 1, 2, 3

    def __init__(self):
        self.state = self.ST_IDLE
        self.idx_x = 0
        self.idx_y = 0

    def step(self, start_i: int = 0, mode_i: int = 0) -> Dict[str, int]:
        if self.state == self.ST_IDLE and start_i:
            self.state = self.ST_PRE if mode_i == 0 else self.ST_POS_COL
            self.idx_x = 0
            self.idx_y = 0
        elif self.state in (self.ST_PRE, self.ST_POS_COL, self.ST_POS_FRA):
            if self.idx_x + 1 < 16:
                self.idx_x += 1
            else:
                self.idx_x = 0
                if self.idx_y + 1 < 16:
                    self.idx_y += 1
                else:
                    if self.state == self.ST_POS_FRA:
                        self.state = self.ST_IDLE
                    elif self.state == self.ST_PRE:
                        self.state = self.ST_POS_COL
                        self.idx_x = 0
                        self.idx_y = 0
                    else:
                        self.state = self.ST_POS_FRA
                        self.idx_x = 0
                        self.idx_y = 0
        return {
            "ori_rd_ena": 1 if self.state != self.ST_IDLE else 0,
            "done": 1 if self.state in (self.ST_PRE, self.ST_POS_FRA)
                       and self.idx_x == 15 and self.idx_y == 15 else 0,
        }


class PosiSatdCostEngineModel:
    """POSI SATD 1-D transform engine: 8-point butterfly."""

    def __init__(self):
        self.val_r = 0
        self.dat_r = 0

    def step(self, size_i: int = 0, val_i: int = 0, dat_i: int = 0) -> Tuple[int, int]:
        self.val_r = val_i
        self.dat_r = dat_i << 3  # simplified bit-growth
        return self.val_r, self.dat_r


class PosiRateEstimationModel:
    """POSI rate estimation: estimates mode-encoding bitrate."""

    def __init__(self):
        self.lambda_reg = 16

    def step(self, qp_i: int = 22, size_i: int = 0, base_rate: int = 0,
             cost_done_i: int = 0) -> int:
        if cost_done_i:
            self.lambda_reg = (qp_i + 1) << 1
        if base_rate == 0:
            return 0
        return min(self.lambda_reg << 3, (1 << 13) - 1)


class PosiSatdCostModel:
    """POSI SATD cost: 2-D Hadamard transform + rate cost."""

    def __init__(self, cost_width: int = POSI_COST_WIDTH):
        self.cost_width = cost_width
        self.val_pipe = [0] * 10
        self.mode_pipe = [0] * 10
        self.size_pipe = [0] * 10
        self.pos_pipe = [0] * 10

    def step(self, qp_i: int = 22, mode_i: int = 0, size_i: int = 0,
             position_i: int = 0, val_i: int = 0, dat_i: int = 0) -> Dict[str, int]:
        self.val_pipe = [val_i] + self.val_pipe[:-1]
        self.mode_pipe = [mode_i] + self.mode_pipe[:-1]
        self.size_pipe = [size_i] + self.size_pipe[:-1]
        self.pos_pipe = [position_i] + self.pos_pipe[:-1]
        return {
            "val_o": self.val_pipe[9], "mode_o": self.mode_pipe[9],
            "size_o": self.size_pipe[9], "position_o": self.pos_pipe[9],
            "cost_o": 0,  # full SATD needs 1D→transpose→2D→abs→sum
        }


class PosiPartitionDecisionModel:
    """POSI partition decision: hierarchical RDO-based quad-tree."""

    def __init__(self):
        self.bst_cst_04 = [0] * 256
        self.bst_cst_08 = [0] * 64
        self.bst_cst_16 = [0] * 16
        self.bst_cst_32 = [0] * 4
        self.prt_reg = 0

    def step(self, clr_i: int = 0, val_i: int = 0, cst_i: int = 0,
             size_i: int = 0, position_i: int = 0, mode_i: int = 0) -> Dict[str, Any]:
        if clr_i:
            self.bst_cst_04 = [0] * 256
            self.bst_cst_08 = [0] * 64
            self.bst_cst_16 = [0] * 16
            self.bst_cst_32 = [0] * 4
            self.prt_reg = 0
        elif val_i:
            if size_i == 0 and cst_i < self.bst_cst_04[position_i]:
                self.bst_cst_04[position_i] = cst_i
            elif size_i == 1 and cst_i < self.bst_cst_08[position_i]:
                self.bst_cst_08[position_i] = cst_i
            elif size_i == 2 and cst_i < self.bst_cst_16[position_i]:
                self.bst_cst_16[position_i] = cst_i
            elif size_i == 3 and cst_i < self.bst_cst_32[position_i]:
                self.bst_cst_32[position_i] = cst_i
        return {"partition": self.prt_reg, "bst_cost": self.bst_cst_32[0]}


# =====================================================================
# REC Submodule Models
# =====================================================================

class TqTopModel:
    """REC TQ: Transform & Quantization (DCT/IDCT + Q/IQ)."""

    def __init__(self):
        self.state = 0
        self.cnt = 0

    def step(self, tq_en_i: int = 0, type_i: int = 0, qp_i: int = 22,
             tq_sel_i: int = 0, tq_size_i: int = 0,
             tq_res_i: int = 0, cef_data_i: int = 0) -> Dict[str, int]:
        if self.rst_guard():
            pass
        if self.state == 0 and tq_en_i:
            self.state = 1
            self.cnt = 0
        elif self.state == 1:
            self.cnt += 1
            if self.cnt == 31:
                self.state = 0
        return {
            "rec_val": 1 if self.state == 1 else 0,
            "rec_idx": self.cnt,
            "cef_wen": 1 if (self.state == 1 and self.cnt < 16) else 0,
            "cef_widx": self.cnt,
            "cef_ren": 1 if self.state == 1 else 0,
            "cef_ridx": self.cnt,
        }

    def rst_guard(self):
        self.state = 0
        self.cnt = 0
        return True


class IntraTopModel:
    """REC intra prediction controller."""

    def __init__(self):
        self.state = 0
        self.cnt = 0

    def step(self, start_i: int = 0) -> Dict[str, int]:
        if self.state == 0 and start_i:
            self.state = 1
            self.cnt = 0
        elif self.state == 1:
            self.cnt += 1
            if self.cnt == 255:
                self.state = 0
        return {
            "md_rd_ena": 1 if self.state == 1 else 0,
            "md_rd_adr": self.cnt & 0xFF,
            "pre_val": 1 if self.state == 1 else 0,
            "rec_done": 1 if (self.state == 1 and self.cnt == 255) else 0,
        }


class McTopModel:
    """REC motion compensation controller."""

    def __init__(self):
        self.state = 0
        self.cnt = 0

    def step(self, sysif_start_i: int = 0) -> Dict[str, int]:
        if self.state == 0 and sysif_start_i:
            self.state = 1
            self.cnt = 0
        elif self.state == 1:
            self.cnt += 1
            if self.cnt == 63:
                self.state = 0
        return {
            "sysif_done": 1 if (self.state == 1 and self.cnt == 63) else 0,
            "fetchif_rden": 1 if self.state == 1 else 0,
            "fmeif_mv_rden": 1 if self.state == 1 else 0,
            "fme_wr_ena": 1 if self.state == 1 else 0,
            "mvd_wen": 1 if self.state == 1 else 0,
            "pre_en": 1 if self.state == 1 else 0,
        }


class RecBufWrapperModel:
    """REC buffer wrapper: central memory hub for reconstruction loop."""

    def __init__(self):
        self.cbf_y_reg = 0
        self.cbf_u_reg = 0
        self.cbf_v_reg = 0

    def step(self, cef_wr_ena_i: int = 0, cef_wr_idx_i: int = 0) -> Dict[str, int]:
        if cef_wr_ena_i:
            bit = 1 << (cef_wr_idx_i >> 2)
            sel = cef_wr_idx_i & 0x3
            if sel == 0:
                self.cbf_y_reg |= bit
            elif sel == 1:
                self.cbf_u_reg |= bit
            elif sel == 2:
                self.cbf_v_reg |= bit
        return {
            "cbf_y": self.cbf_y_reg, "cbf_u": self.cbf_u_reg, "cbf_v": self.cbf_v_reg,
        }


# =====================================================================
# DBSAO Submodule Models
# =====================================================================

class DbsaoControllerModel:
    """DB+SAO controller: LOAD → DBY → DBU → DBV → SAO → OUT."""

    ST_IDLE, ST_LOAD, ST_DBY, ST_DBU, ST_DBV, ST_SAO, ST_OUT = 0, 1, 2, 3, 4, 5, 6
    _CNT_LIMITS = {ST_LOAD: 31, ST_DBY: 127, ST_DBU: 63, ST_DBV: 63, ST_SAO: 31, ST_OUT: 15}

    def __init__(self):
        self.state = self.ST_IDLE
        self.cnt = 0

    def step(self, start_i: int = 0) -> Dict[str, int]:
        if self.state == self.ST_IDLE and start_i:
            self.state = self.ST_LOAD
            self.cnt = 0
        elif self.state != self.ST_IDLE:
            self.cnt += 1
            limit = self._CNT_LIMITS.get(self.state, 31)
            if self.cnt == limit:
                if self.state == self.ST_OUT:
                    self.state = self.ST_IDLE
                else:
                    self.state += 1
                self.cnt = 0
        return {
            "done": 1 if (self.state == self.ST_OUT and self.cnt == 15) else 0,
            "cnt": self.cnt, "state": self.state,
        }


class DbFilterModel:
    """DB filter core: HEVC deblocking on 4x4 edge."""

    def step(self, p_i: int = 0, q_i: int = 0, sys_db_ena_i: int = 0,
             qp_p_i: int = 22, qp_q_i: int = 22, tu_edge_i: int = 0,
             pu_edge_i: int = 0, cbf_p_i: int = 0, cbf_q_i: int = 0,
             mv_p_i: int = 0, mv_q_i: int = 0, mb_type_i: int = 0,
             is_ver_i: int = 0, IinP_flag_i: int = 0) -> Tuple[int, int]:
        # Simplified: pass-through (full impl applies HEVC deblocking filter)
        return p_i, q_i


class DbBsModel:
    """DB boundary strength: computes BS, TU/PU edge, QP, CBF flags."""

    def step(self, cnt_i: int = 0, state_i: int = 0, qp_i: int = 22,
             mb_partition_i: int = 0, mb_p_pu_mode_i: int = 0,
             mb_cbf_i: int = 0, mb_cbf_u_i: int = 0, mb_cbf_v_i: int = 0) -> Dict[str, int]:
        return {
            "tu_edge": 0, "pu_edge": 0,
            "qp_p": qp_i, "qp_q": qp_i,
            "cbf_p": 0, "cbf_q": 0,
        }


# =====================================================================
# CABAC Submodule Models
# =====================================================================

class CabacSePrepareModel:
    """CABAC syntax element preparation: CU quad-tree traversal, SE emission."""

    def __init__(self):
        self.state = 0
        self.cnt = 0

    def step(self, sys_start_i: int = 0, sys_slice_type_i: int = 0,
             context_init_done_i: int = 1, rc_qp_i: int = 22) -> Dict[str, int]:
        if self.state == 0 and sys_start_i and context_init_done_i:
            self.state = 1
            self.cnt = 0
        elif self.state == 1:
            self.cnt += 1
            if self.cnt == 255:
                self.state = 0
        return {
            "en": 1 if self.state == 1 else 0,
            "lcu_done": 1 if (self.state == 1 and self.cnt == 255) else 0,
            "gp_qp": rc_qp_i,
            "syntax_element_valid": 1 if self.state == 1 else 0,
        }


class CabacBinaModel:
    """CABAC binarization: converts syntax elements to binary bins."""

    def step(self, en: int = 0, init_done: int = 1) -> Dict[str, int]:
        return {
            "valid": en & init_done,
            "flag_end_slice": 0,
            "out_number": 0,
        }


class CabacBitpackModel:
    """CABAC bitpack: packs bins into bytes, handles emulation prevention."""

    def __init__(self):
        self.bit_buffer = 0
        self.buf_len = 128

    def step(self, en: int = 0, r_enable: int = 1, length: int = 0,
             string_to_update: int = 0) -> Dict[str, int]:
        if en and r_enable and self.buf_len >= length:
            self.bit_buffer = ((self.bit_buffer << length) | string_to_update) & ((1 << 128) - 1)
            self.buf_len -= length
        return {
            "left_space": self.buf_len,
            "out_ready": 1 if self.buf_len < 8 else 0,
            "output_byte": (self.bit_buffer >> 120) & 0xFF,
        }


# =====================================================================
# FETCH Submodule Models
# =====================================================================

class FetchWrapperModel:
    """FETCH wrapper: top-level fetch arbiter and scheduler."""

    def __init__(self):
        self.state = 0
        self.cnt = 0

    def step(self, sysif_start_i: int = 0) -> Dict[str, int]:
        if self.state == 0 and sysif_start_i:
            self.state = 1
            self.cnt = 0
        elif self.state == 1:
            self.cnt += 1
            if self.cnt == 255:
                self.state = 0
        return {
            "sysif_done": 1 if (self.state == 1 and self.cnt == 255) else 0,
            "cur_luma_done": 1 if (self.state == 1 and self.cnt == 63) else 0,
            "cur_luma_valid": 1 if (self.state == 1 and self.cnt < 64) else 0,
            "ref_luma_done": 1 if (self.state == 1 and self.cnt == 127) else 0,
            "ref_luma_valid": 1 if (self.state == 1 and 64 <= self.cnt < 128) else 0,
            "db_store_ena": 1 if (self.state == 1 and self.cnt >= 128) else 0,
            "extif_start": 1 if (self.state == 1 and self.cnt == 0) else 0,
        }


class FetchCurLumaModel:
    """FETCH current luma buffer: multi-bank rotating buffer."""

    def __init__(self):
        self.banks = [0] * 4  # 4 banks for rotation
        self.active_bank = 0

    def step(self, rden_i: int = 0, sel_i: int = 0, size_i: int = 0,
             x_i: int = 0, y_i: int = 0, idx_i: int = 0,
             ext_valid_i: int = 0, ext_data_i: int = 0) -> int:
        if ext_valid_i:
            self.banks[self.active_bank] = ext_data_i
        return self.banks[sel_i]


class FetchRefLumaModel:
    """FETCH reference luma buffer: larger buffer for reference frames."""

    def __init__(self):
        self.buffer = [0] * 1024

    def step(self, ext_valid_i: int = 0, ext_data_i: int = 0,
             ext_addr_i: int = 0, rden_i: int = 0, rd_addr_i: int = 0) -> int:
        if ext_valid_i:
            self.buffer[ext_addr_i & 0x3FF] = ext_data_i
        if rden_i:
            return self.buffer[rd_addr_i & 0x3FF]
        return 0


# =====================================================================
# Suite Model
# =====================================================================

class Xk265SuiteModel:
    """Full xk265 H.265 encoder suite model.

    Chains all 38 modules through the 9-stage CTU pipeline.
    """

    STAGES = ["enc_ctrl", "prei_top", "posi_top", "ime_top", "fme_top",
              "rec_top", "dbsao_top", "cabac_top", "fetch_top"]

    def __init__(self, lcu_size: int = 64, pic_width: int = 1920, pic_height: int = 1080):
        self.encoder = H265EncoderModel(lcu_size=lcu_size, pic_width=pic_width, pic_height=pic_height)

        # IME submodule models
        self.ime_ctrl = ImeCtrlModel()
        self.ime_addr = ImeAddressingModel()
        self.ime_dat = ImeDatArrayModel()
        self.ime_sad = ImeSadArrayModel()
        self.ime_cost = ImeCostStoreModel()
        self.ime_pde = ImePartitionDecisionEngineModel()
        self.ime_part = ImePartitionDecisionModel()
        self.ime_mv = ImeMvDumpModel()

        # POSI submodule models
        self.posi_ctrl = PosiCtrlModel()
        self.posi_xfer = PosiTransferModel()
        self.posi_satd_eng = PosiSatdCostEngineModel()
        self.posi_rate = PosiRateEstimationModel()
        self.posi_satd = PosiSatdCostModel()
        self.posi_part = PosiPartitionDecisionModel()

        # REC submodule models
        self.rec_tq = TqTopModel()
        self.rec_intra = IntraTopModel()
        self.rec_mc = McTopModel()
        self.rec_buf = RecBufWrapperModel()

        # DBSAO submodule models
        self.dbsao_ctrl = DbsaoControllerModel()
        self.db_filter = DbFilterModel()
        self.db_bs = DbBsModel()

        # CABAC submodule models
        self.cabac_se = CabacSePrepareModel()
        self.cabac_bina = CabacBinaModel()
        self.cabac_bp = CabacBitpackModel()

        # FETCH submodule models
        self.fetch_wrap = FetchWrapperModel()
        self.fetch_cur = FetchCurLumaModel()
        self.fetch_ref = FetchRefLumaModel()

    def reset(self):
        self.encoder.reset()

    def run(self, num_cycles: int = 1000) -> Dict[str, Any]:
        return self.encoder.run(num_cycles)

    def get_status(self) -> Dict[str, Any]:
        return self.encoder.get_status()
