"""L2 Cycle-Accurate Models — RISC-V 64 CPU pipeline."""
from __future__ import annotations
from typing import Callable
from rtlgen.arch_def import CycleContext
from rtlgen.registry import TemplateRegistry
from skills.cpu_riscv64 import *


def fetch_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 Fetch: 2-stage fetch pipeline (PCGen + I-Cache)."""
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input("rst", 0)
        if rst:
            ctx.state["pc"] = 0x1000; ctx.state["f1_valid"] = 0
            ctx.state["f2_valid"] = 0; ctx.state["stall"] = 0
            return
        branch = ctx.get_input("branch_taken", 0)
        btarget = ctx.get_input("branch_target", 0)
        stall = ctx.get_input("stall_fetch", 0)
        pc = ctx.state.get("pc", 0x1000)
        if branch:
            ctx.state["pc"] = btarget
        elif not stall:
            ctx.state["pc"] = pc + 4
        ctx.state["f2_valid"] = ctx.state.get("f1_valid", 0)
        ctx.state["f1_valid"] = 1
        ctx.set_output("fetch_pc", ctx.state["pc"])
        ctx.set_output("fetch_valid", ctx.state["f2_valid"])
    return behavior


def execute_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 Execute: ALU with multi-cycle operations."""
    mul_lat = kwargs.get('mul_lat', L_MUL)
    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input("rst", 0)
        if rst:
            ctx.state["pipe_valid"] = 0; ctx.state["mul_cnt"] = 0
            ctx.state["result"] = 0
            return
        op = ctx.get_input("opcode", 0)
        rs1 = ctx.get_input("rs1_val", 0); rs2 = ctx.get_input("rs2_val", 0)
        funct3 = ctx.get_input("funct3", 0); funct7 = ctx.get_input("funct7", 0)
        imm = ctx.get_input("imm", 0)
        valid = ctx.get_input("in_valid", 0)
        mul_active = ctx.state.get("mul_cnt", 0) > 0

        if mul_active:
            ctx.state["mul_cnt"] = ctx.state["mul_cnt"] - 1
            if ctx.state["mul_cnt"] == 0:
                ctx.set_output("result", ctx.state["mul_acc"])
                ctx.set_output("out_valid", 1)
            return

        if valid:
            result = 0
            is_mul = (funct7 == 1 and funct3 == 0)
            if is_mul:
                ctx.state["mul_cnt"] = mul_lat - 1
                ctx.state["mul_acc"] = (rs1 * rs2) & ((1 << XLEN) - 1)
            elif op == OP_RI or op == OP_RR:
                b = rs2 if op == OP_RR else imm
                if funct3 == 0: result = rs1 + b
                elif funct3 == 1: result = rs1 << (b & 0x3F)
                elif funct3 == 2: result = 1 if rs1 < b else 0
                elif funct3 == 3: result = 1 if (rs1 & ((1<<XLEN)-1)) < (b & ((1<<XLEN)-1)) else 0
                elif funct3 == 4: result = rs1 ^ b
                elif funct3 == 5: result = rs1 >> (b & 0x3F) if funct7 == 0 else (rs1 >> (b & 0x3F))
                elif funct3 == 6: result = rs1 | b
                elif funct3 == 7: result = rs1 & b
                ctx.set_output("result", result & ((1 << XLEN) - 1))
                ctx.set_output("out_valid", 1)
    return behavior


def fpu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """L2 FPU: multi-cycle FP operations with pipeline."""

    def _fpu_lat(f7: int) -> int:
        f7_top = f7 & 0x1F
        return {FUNC_FADD: L_FADD, FUNC_FSUB: L_FADD, FUNC_FMUL: L_FMUL,
                FUNC_FDIV: L_FMUL, FUNC_FSQRT: L_FSQRT}.get(f7_top, L_FADD)

    def behavior(ctx: CycleContext) -> None:
        rst = ctx.get_input("rst", 0)
        if rst:
            for k in ["fp_cnt", "fp_result"]: ctx.state[k] = 0
            return
        f7_raw = ctx.get_input("funct7", 0)
        valid = ctx.get_input("in_valid", 0)
        cnt = ctx.state.get("fp_cnt", 0)

        if cnt > 0:
            ctx.state["fp_cnt"] = cnt - 1
            if cnt == 1:
                ctx.set_output("result", ctx.state["fp_result"])
                ctx.set_output("out_valid", 1)
            return

        if valid:
            lat = _fpu_lat(f7_raw)
            ctx.state["fp_cnt"] = lat - 1
            ctx.state["fp_result"] = ctx.get_input("result", 0)
    return behavior


TemplateRegistry.register("fetch", fetch_cycle)
TemplateRegistry.register("execute", execute_cycle)
TemplateRegistry.register("fpu", fpu_cycle)
