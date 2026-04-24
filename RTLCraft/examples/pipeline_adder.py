#!/usr/bin/env python3
"""流水线加法器示例：演示 Pipeline、Stage、Handshake 的自动握手与级间寄存器。"""

import sys
sys.path.insert(0, "..")

from rtlgen import Pipeline, Input, VerilogEmitter


pipe = Pipeline("AdderPipe", data_width=32, has_handshake=True)
pipe.clk = Input(1, "clk")
pipe.rst = Input(1, "rst")


@pipe.stage(0)
def fetch(ctx):
    temp = ctx.local("temp", 32)
    temp <<= ctx.in_hs.data + 1
    ctx.out_hs.data <<= temp
    ctx.out_hs.valid <<= ctx.in_hs.valid


@pipe.stage(1)
def exec_(ctx):
    ctx.out_hs.data <<= ctx.in_hs.data + 2
    ctx.out_hs.valid <<= ctx.in_hs.valid


pipe.build()

if __name__ == "__main__":
    emitter = VerilogEmitter()
    print(emitter.emit(pipe))
