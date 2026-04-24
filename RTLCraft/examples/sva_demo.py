#!/usr/bin/env python3
"""
SVA 自动生成示例：为 Counter 和 Pipeline Adder 生成断言。
"""

import sys
sys.path.insert(0, "..")

from rtlgen import SVAEmitter, Pipeline, Input
from counter import Counter


if __name__ == "__main__":
    sva = SVAEmitter()

    print("// ===== Counter Assertions =====")
    counter = Counter(width=8)
    print(sva.emit_assertions(counter))

    print("// ===== Pipeline Adder Assertions =====")
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
    print(sva.emit_assertions(
        pipe,
        custom_assertions=[
            ("valid_implies_ready_or_stable", "valid_out |-> (ready_in || $stable(data_out))"),
        ]
    ))
