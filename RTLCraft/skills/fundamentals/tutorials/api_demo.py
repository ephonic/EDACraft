#!/usr/bin/env python3
"""
API Demo: comments, assertions, and suggestions passed into generated Verilog.

运行:
    PYTHONPATH=.. python api_demo.py
"""
import sys
sys.path.insert(0, "..")

from rtlgen import Module, Input, Output, VerilogEmitter
from rtlgen.logic import Const
from rtlgen.ppa import PPAAnalyzer


class Demo(Module):
    def __init__(self):
        super().__init__("demo")
        self.clk = Input(1, "clk")
        self.rst_n = Input(1, "rst_n")
        self.a = Input(8, "a")
        self.b = Input(8, "b")
        self.y = Output(8, "y")

        # 1. 通过 API 添加模块级注释
        self.add_comment("Module: demo")
        self.add_comment("Function: y = a + b with saturation")

        # 2. 通过 API 添加自定义 SVA 断言
        self.add_assertion("sum_lt_256", "(a + b) < 256")

        # 3. 通过 PPAAnalyzer 获取建议并注入到 Verilog 头部
        analyzer = PPAAnalyzer(self)
        static = analyzer.analyze_static()
        suggestions = analyzer.suggest_optimizations(static)
        if suggestions:
            self.add_suggestions(suggestions)

        @self.comb
        def _logic():
            self.y <<= self.a + self.b


if __name__ == "__main__":
    top = Demo()
    emitter = VerilogEmitter()

    print("=" * 60)
    print("Generated Verilog (without SVA):")
    print("=" * 60)
    print(emitter.emit_design(top))

    print("\n" + "=" * 60)
    print("Generated Verilog (with SVA assertions):")
    print("=" * 60)
    print(emitter.emit_design(top, include_assertions=True))
