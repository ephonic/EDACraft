#!/usr/bin/env python3
"""红绿灯状态机示例：演示新版模块化 FSM 的用法。

所有输出与状态转移均定义在 FSM 内部，通过 fsm.build(parent=self) 自动嵌入父模块。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import FSM, Module, Input, Output, VerilogEmitter


class TrafficLight(Module):
    def __init__(self):
        super().__init__("TrafficLight")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.timer_done = Input(1, "timer_done")

        fsm = FSM("RED", name="")
        fsm.add_output("red", width=1, default=0)
        fsm.add_output("yellow", width=1, default=0)
        fsm.add_output("green", width=1, default=0)

        @fsm.state("RED")
        def red(ctx):
            ctx.red = 1
            ctx.yellow = 0
            ctx.green = 0
            ctx.goto("GREEN", when=self.timer_done)

        @fsm.state("GREEN")
        def green(ctx):
            ctx.red = 0
            ctx.yellow = 0
            ctx.green = 1
            ctx.goto("YELLOW", when=self.timer_done)

        @fsm.state("YELLOW")
        def yellow(ctx):
            ctx.red = 0
            ctx.yellow = 1
            ctx.green = 0
            ctx.goto("RED", when=self.timer_done)

        fsm.build(self.clk, self.rst, parent=self)


if __name__ == "__main__":
    top = TrafficLight()
    emitter = VerilogEmitter()
    print(emitter.emit(top))
