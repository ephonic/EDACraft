"""
skills/thor/models — Thor GPGPU Golden Reference Models.

Cycle-accurate Python simulators for SM and full GPU.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from skills.thor import (
    XLEN, NLANE, VLEN, VREGS, NWARP, NSM, IMEM_DEPTH,
    OP_NOP, OP_SLOAD, OP_VLOAD, OP_VSTORE, OP_VADD, OP_VMUL,
    OP_VMLA, OP_BARRIER, OP_DONE, decode_inst,
)


class ThorSM_Model:
    """Cycle-accurate SM behavioral model (golden reference).
    
    Per-warp FSM:
      0 = idle (ready for fetch)
      1 = fetch + execute (or start memory)
      3 = memory wait
      0xF = done
    """

    def __init__(self, nwarp: int = 4, vregs: int = 8, imem_depth: int = 32):
        self.nwarp = nwarp
        self.vregs = vregs
        self.imem_depth = imem_depth
        self.warp_pc = [0] * nwarp
        self.warp_state = [0] * nwarp
        self.warp_done = [0] * nwarp
        self.warp_inst = [0] * nwarp
        self.imem = [0] * imem_depth
        self.vrf = [0] * (vregs * nwarp)
        self.warp_sel = 0
        self.running = 0
        self.cycle = 0

    def load_imem(self, addr: int, data: int):
        self.imem[addr % self.imem_depth] = data

    def step(self, start: int = 0, mem_valid: int = 0,
             mem_rdata: int = 0, mem_ready: int = 1) -> Dict[str, Any]:
        self.cycle += 1
        nw = self.nwarp; vr = self.vregs
        if start and not self.running:
            self.running = 1
            self.warp_pc = [0] * nw
            self.warp_state = [0] * nw
            self.warp_done = [0] * nw
            self.warp_inst = [0] * nw
            self.warp_sel = 0

        if not self.running:
            return {"mem_req": 0, "sm_done": 0}

        w = self.warp_sel
        st = self.warp_state[w]
        mem_req = 0; mem_wen = 0; mem_addr = 0; mem_wdata = 0
        mask_v = (1 << VLEN) - 1
        mask_x = (1 << XLEN) - 1

        if st == 0:
            self.warp_state[w] = 1

        elif st == 1:
            inst = self.imem[self.warp_pc[w] % self.imem_depth]
            self.warp_inst[w] = inst
            self.warp_pc[w] = (self.warp_pc[w] + 1) % self.imem_depth
            opcode, rd, rs1, rs2, imm = decode_inst(inst)

            if opcode == OP_SLOAD:
                vec = 0
                lane_val = imm & mask_x
                for lane in range(NLANE):
                    vec |= lane_val << (lane * XLEN)
                self.vrf[w * vr + rd] = vec
                self.warp_state[w] = 0
            elif opcode in (OP_VADD, OP_VMUL):
                a_packed = self.vrf[w * vr + rs1]
                b_packed = self.vrf[w * vr + rs2]
                result = 0
                for lane in range(NLANE):
                    a_lane = (a_packed >> (lane * XLEN)) & mask_x
                    b_lane = (b_packed >> (lane * XLEN)) & mask_x
                    if opcode == OP_VADD:
                        r_lane = (a_lane + b_lane) & mask_x
                    else:
                        r_lane = (a_lane * b_lane) & mask_x
                    result |= r_lane << (lane * XLEN)
                self.vrf[w * vr + rd] = result
                self.warp_state[w] = 0
            elif opcode == OP_VLOAD:
                self.warp_state[w] = 3
                mem_req = 1
                mem_addr = imm & 0xFFFFFFFF
            elif opcode == OP_VSTORE:
                self.warp_state[w] = 3
                mem_req = 1
                mem_addr = imm & 0xFFFFFFFF
                mem_wen = 1
                mem_wdata = self.vrf[w * vr + rs1]
            elif opcode == OP_DONE:
                self.warp_done[w] = 1
                self.warp_state[w] = 0xF
            else:
                self.warp_state[w] = 0

        elif st == 3:
            if mem_valid and mem_ready:
                opcode, rd, rs1, rs2, imm = decode_inst(self.warp_inst[w])
                if opcode == OP_VLOAD:
                    self.vrf[w * vr + rd] = mem_rdata
                self.warp_state[w] = 0

        next_sel = w
        if self.warp_state[w] == 0 or self.warp_state[w] == 0xF:
            for i in range(1, nw + 1):
                nw2 = (w + i) % nw
                if not self.warp_done[nw2] and self.warp_state[nw2] == 0:
                    next_sel = nw2
                    break
        self.warp_sel = next_sel

        sm_done = all(self.warp_done)
        return {
            "mem_req": mem_req, "mem_wen": mem_wen,
            "mem_addr": mem_addr, "mem_wdata": mem_wdata,
            "sm_done": int(sm_done),
        }


class ThorGPU_Model:
    """Full Thor GPGPU golden reference model."""

    def __init__(self, n_sm: int = NSM, nwarp: int = 4):
        self.sms = [ThorSM_Model(nwarp=nwarp) for _ in range(n_sm)]
        self.n_sm = n_sm
        self.nwarp = nwarp
        self.cycle = 0
        self.rr_grant = 0

    def step(self, start: int = 0, mem_rdata: int = 0, mem_ready: int = 1) -> Dict:
        self.cycle += 1
        sm_results = []
        for sm in self.sms:
            r = sm.step(start=start, mem_ready=mem_ready)
            sm_results.append(r)

        any_req = any(r["mem_req"] for r in sm_results)
        if any_req and mem_ready:
            self.rr_grant = 1 - self.rr_grant

        grant = self.rr_grant
        active = sm_results[grant]
        all_done = all(r["sm_done"] for r in sm_results)

        return {
            "mem_req": active["mem_req"],
            "mem_wen": active["mem_wen"],
            "mem_addr": active["mem_addr"],
            "mem_wdata": active["mem_wdata"],
            "all_done": int(all_done),
            "cycle": self.cycle,
        }

    def load_imem(self, sm_id: int, addr: int, data: int):
        self.sms[sm_id].load_imem(addr, data)

    def run(self, num_cycles: int = 200, mem_rdata: int = 0,
            mem_ready: int = 1) -> Dict:
        start = 1
        for _ in range(num_cycles):
            result = self.step(start=start, mem_rdata=mem_rdata, mem_ready=mem_ready)
            start = 0
            if result["all_done"]:
                return result
        return result
