#!/usr/bin/env python3
"""Test pipeline lint checks on a buggy ALULane module."""

import sys
sys.path.insert(0, ".")

# Import directly from the modules to avoid loading uvmgen (has syntax error)
from rtlgen.core import Input, Output, Wire, Reg, Module
from rtlgen.codegen import VerilogEmitter


# Simplified ISA constants for testing
class isa:
    ALU_ADD = 0b000000
    ALU_SUB = 0b000001
    ALU_MUL = 0b000010
    ALU_MAD = 0b000011
    ALU_AND = 0b000100
    ALU_OR  = 0b000101
    ALU_XOR = 0b000110
    ALU_NOT = 0b000111
    ALU_SHL = 0b001000
    ALU_SHR = 0b001001
    ALU_ASR = 0b001010
    ALU_MIN = 0b001011
    ALU_MAX = 0b001100
    ALU_ABS = 0b001101
    ALU_NEG = 0b001110
    ALU_FADD = 0b010000
    ALU_FSUB = 0b010001
    ALU_FMUL = 0b010010
    ALU_FMAD = 0b010011
    ALU_FMIN = 0b010100
    ALU_FMAX = 0b010101
    ALU_FABS = 0b010110
    ALU_FNEG = 0b010111
    ALU_SETP_EQ = 0b100000
    ALU_SETP_NE = 0b100001
    ALU_SETP_LT = 0b100010
    ALU_SETP_LE = 0b100011
    ALU_SETP_GT = 0b100100
    ALU_SETP_GE = 0b100101
    MOV_MOV = 0b110000
    MOV_SEL = 0b110001


def Mux(cond, true_val, false_val):
    from rtlgen.logic import Mux as _Mux
    return _Mux(cond, true_val, false_val)


class ALULaneBuggy(Module):
    """Buggy ALULane: result_r/pred_r assigned in @comb instead of @seq."""

    def __init__(self, data_width: int = 32):
        super().__init__("ALULaneBuggy")
        self.data_width = data_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Control
        self.valid = Input(1, "valid")
        self.op = Input(6, "op")
        self.shift_amt = Input(5, "shift_amt")

        # Operands
        self.src_a = Input(data_width, "src_a")
        self.src_b = Input(data_width, "src_b")
        self.src_c = Input(data_width, "src_c")

        # Outputs
        self.out_valid = Output(1, "out_valid")
        self.result = Output(data_width, "result")
        self.pred_out = Output(1, "pred_out")

        # Internal result wires for each operation group
        self.int_result = Wire(data_width, "int_result")
        self.fp_result = Wire(data_width, "fp_result")
        self.cmp_result = Wire(1, "cmp_result")
        self.pred_result = Wire(1, "pred_result")
        self.mov_result = Wire(data_width, "mov_result")

        # Registered outputs (should be in @seq, but placed in @comb - BUG)
        self.result_r = Reg(data_width, "result_r")
        self.pred_r = Reg(1, "pred_r")
        self.valid_r = Reg(1, "valid_r")

        from rtlgen.logic import If

        @self.comb
        def _compute():
            a = self.src_a
            b = self.src_b
            c = self.src_c
            op = self.op

            # Default results
            self.int_result <<= 0
            self.fp_result <<= 0
            self.cmp_result <<= 0
            self.pred_result <<= 0
            self.mov_result <<= 0

            # Integer operations
            with If(op == isa.ALU_ADD):
                self.int_result <<= a + b
            with If(op == isa.ALU_SUB):
                self.int_result <<= a - b
            with If(op == isa.ALU_MUL):
                self.int_result <<= a * b
            with If(op == isa.ALU_MAD):
                self.int_result <<= (a * b) + c
            with If(op == isa.ALU_AND):
                self.int_result <<= a & b
            with If(op == isa.ALU_OR):
                self.int_result <<= a | b
            with If(op == isa.ALU_XOR):
                self.int_result <<= a ^ b
            with If(op == isa.ALU_NOT):
                self.int_result <<= ~a
            with If(op == isa.ALU_SHL):
                self.int_result <<= a << self.shift_amt
            with If(op == isa.ALU_SHR):
                self.int_result <<= a >> self.shift_amt
            with If(op == isa.ALU_ASR):
                self.int_result <<= a >> self.shift_amt
            with If(op == isa.ALU_MIN):
                self.int_result <<= Mux(a < b, a, b)
            with If(op == isa.ALU_MAX):
                self.int_result <<= Mux(a > b, a, b)
            with If(op == isa.ALU_ABS):
                self.int_result <<= Mux(a[data_width - 1] == 1, 0 - a, a)
            with If(op == isa.ALU_NEG):
                self.int_result <<= 0 - a

            # FP operations
            with If(op == isa.ALU_FADD):
                self.fp_result <<= a + b
            with If(op == isa.ALU_FSUB):
                self.fp_result <<= a - b
            with If(op == isa.ALU_FMUL):
                self.fp_result <<= a * b
            with If(op == isa.ALU_FMAD):
                self.fp_result <<= (a * b) + c
            with If(op == isa.ALU_FMIN):
                self.fp_result <<= Mux(a < b, a, b)
            with If(op == isa.ALU_FMAX):
                self.fp_result <<= Mux(a > b, a, b)
            with If(op == isa.ALU_FABS):
                self.fp_result <<= Mux(a[data_width - 1] == 1, 0 - a, a)
            with If(op == isa.ALU_FNEG):
                self.fp_result <<= 0 - a

            # Comparison
            with If(op == isa.ALU_SETP_EQ):
                self.cmp_result <<= (a == b)
            with If(op == isa.ALU_SETP_NE):
                self.cmp_result <<= (a != b)
            with If(op == isa.ALU_SETP_LT):
                self.cmp_result <<= (a < b)
            with If(op == isa.ALU_SETP_LE):
                self.cmp_result <<= (a <= b)
            with If(op == isa.ALU_SETP_GT):
                self.cmp_result <<= (a > b)
            with If(op == isa.ALU_SETP_GE):
                self.cmp_result <<= (a >= b)

            # Move / Select
            with If(op == isa.MOV_MOV):
                self.mov_result <<= a
            with If(op == isa.MOV_SEL):
                self.mov_result <<= Mux(self.pred_out, a, b)

            # Final mux: select result based on opcode range
            is_fp = (op >> 4) == 0b01
            is_cmp = (op >> 4) == 0b10

            # BUG: result_r and pred_r should be in @seq, not @comb
            self.result_r <<= Mux(is_cmp, 0, Mux(is_fp, self.fp_result, self.int_result))
            self.pred_r <<= Mux(is_cmp, self.cmp_result, 0)

        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _reg():
            self.valid_r <<= self.valid

        # Top-level output connections
        self.out_valid <<= self.valid_r
        self.result <<= self.result_r
        self.pred_out <<= self.pred_r


class ALULaneFixed(Module):
    """Fixed ALULane: result_r/pred_r correctly assigned in @seq."""

    def __init__(self, data_width: int = 32):
        super().__init__("ALULaneFixed")
        self.data_width = data_width

        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")

        # Control
        self.valid = Input(1, "valid")
        self.op = Input(6, "op")
        self.shift_amt = Input(5, "shift_amt")

        # Operands
        self.src_a = Input(data_width, "src_a")
        self.src_b = Input(data_width, "src_b")
        self.src_c = Input(data_width, "src_c")

        # Outputs
        self.out_valid = Output(1, "out_valid")
        self.result = Output(data_width, "result")
        self.pred_out = Output(1, "pred_out")

        # Internal result wires
        self.int_result = Wire(data_width, "int_result")
        self.fp_result = Wire(data_width, "fp_result")
        self.cmp_result = Wire(1, "cmp_result")
        self.pred_result = Wire(1, "pred_result")
        self.mov_result = Wire(data_width, "mov_result")

        # Registered outputs
        self.result_r = Reg(data_width, "result_r")
        self.pred_r = Reg(1, "pred_r")
        self.valid_r = Reg(1, "valid_r")

        from rtlgen.logic import If

        @self.comb
        def _compute():
            a = self.src_a
            b = self.src_b
            c = self.src_c
            op = self.op

            # Default results
            self.int_result <<= 0
            self.fp_result <<= 0
            self.cmp_result <<= 0
            self.pred_result <<= 0
            self.mov_result <<= 0

            # Integer operations
            with If(op == isa.ALU_ADD):
                self.int_result <<= a + b
            with If(op == isa.ALU_SUB):
                self.int_result <<= a - b
            with If(op == isa.ALU_MUL):
                self.int_result <<= a * b
            with If(op == isa.ALU_MAD):
                self.int_result <<= (a * b) + c
            with If(op == isa.ALU_AND):
                self.int_result <<= a & b
            with If(op == isa.ALU_OR):
                self.int_result <<= a | b
            with If(op == isa.ALU_XOR):
                self.int_result <<= a ^ b
            with If(op == isa.ALU_NOT):
                self.int_result <<= ~a
            with If(op == isa.ALU_SHL):
                self.int_result <<= a << self.shift_amt
            with If(op == isa.ALU_SHR):
                self.int_result <<= a >> self.shift_amt
            with If(op == isa.ALU_ASR):
                self.int_result <<= a >> self.shift_amt
            with If(op == isa.ALU_MIN):
                self.int_result <<= Mux(a < b, a, b)
            with If(op == isa.ALU_MAX):
                self.int_result <<= Mux(a > b, a, b)
            with If(op == isa.ALU_ABS):
                self.int_result <<= Mux(a[data_width - 1] == 1, 0 - a, a)
            with If(op == isa.ALU_NEG):
                self.int_result <<= 0 - a

            # FP operations
            with If(op == isa.ALU_FADD):
                self.fp_result <<= a + b
            with If(op == isa.ALU_FSUB):
                self.fp_result <<= a - b
            with If(op == isa.ALU_FMUL):
                self.fp_result <<= a * b
            with If(op == isa.ALU_FMAD):
                self.fp_result <<= (a * b) + c
            with If(op == isa.ALU_FMIN):
                self.fp_result <<= Mux(a < b, a, b)
            with If(op == isa.ALU_FMAX):
                self.fp_result <<= Mux(a > b, a, b)
            with If(op == isa.ALU_FABS):
                self.fp_result <<= Mux(a[data_width - 1] == 1, 0 - a, a)
            with If(op == isa.ALU_FNEG):
                self.fp_result <<= 0 - a

            # Comparison
            with If(op == isa.ALU_SETP_EQ):
                self.cmp_result <<= (a == b)
            with If(op == isa.ALU_SETP_NE):
                self.cmp_result <<= (a != b)
            with If(op == isa.ALU_SETP_LT):
                self.cmp_result <<= (a < b)
            with If(op == isa.ALU_SETP_LE):
                self.cmp_result <<= (a <= b)
            with If(op == isa.ALU_SETP_GT):
                self.cmp_result <<= (a > b)
            with If(op == isa.ALU_SETP_GE):
                self.cmp_result <<= (a >= b)

            # Move / Select
            with If(op == isa.MOV_MOV):
                self.mov_result <<= a
            with If(op == isa.MOV_SEL):
                self.mov_result <<= Mux(self.pred_out, a, b)

        # FIXED: result_r and pred_r assigned in @seq
        @self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
        def _reg():
            self.valid_r <<= self.valid
            is_fp = (self.op >> 4) == 0b01
            is_cmp = (self.op >> 4) == 0b10
            self.result_r <<= Mux(is_cmp, 0, Mux(is_fp, self.fp_result, self.int_result))
            self.pred_r <<= Mux(is_cmp, self.cmp_result, 0)

        # Top-level output connections
        self.out_valid <<= self.valid_r
        self.result <<= self.result_r
        self.pred_out <<= self.pred_r


def main():
    print("=" * 70)
    print("TEST 1: Buggy ALULane - lint should detect violations")
    print("=" * 70)

    buggy = ALULaneBuggy()

    # Run AST-level lint
    print("\n--- AST-level lint (Module.lint) ---")
    ast_violations = buggy.lint()
    if ast_violations:
        for v in ast_violations:
            print(f"  VIOLATION: {v}")
    else:
        print("  No violations found (UNEXPECTED)")

    # Run Verilog-level lint
    print("\n--- Verilog-level lint (VerilogLinter) ---")
    emitter = VerilogEmitter()
    verilog, lint_result = emitter.emit_with_lint(buggy)
    if lint_result.issues:
        for issue in lint_result.issues:
            print(f"  [{issue.severity}] Line {issue.line}: {issue.rule}: {issue.message}")
    else:
        print("  No issues found")

    print("\n" + "=" * 70)
    print("TEST 2: Fixed ALULane - lint should pass")
    print("=" * 70)

    fixed = ALULaneFixed()

    print("\n--- AST-level lint (Module.lint) ---")
    ast_violations = fixed.lint()
    if ast_violations:
        for v in ast_violations:
            print(f"  VIOLATION: {v}")
    else:
        print("  No violations found (EXPECTED)")

    print("\n--- Verilog-level lint (VerilogLinter) ---")
    emitter2 = VerilogEmitter()
    verilog2, lint_result2 = emitter2.emit_with_lint(fixed)
    if lint_result2.issues:
        for issue in lint_result2.issues:
            print(f"  [{issue.severity}] Line {issue.line}: {issue.rule}: {issue.message}")
    else:
        print("  No issues found (EXPECTED)")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"  Buggy version: {len(buggy.lint())} AST violations, "
          f"{len(lint_result.issues)} Verilog issues")
    print(f"  Fixed version: {len(fixed.lint())} AST violations, "
          f"{len(lint_result2.issues)} Verilog issues")


if __name__ == "__main__":
    main()
