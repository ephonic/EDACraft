#!/usr/bin/env python3
"""RAM 使用示例：单口 RAM 与简单双口 RAM。"""

import sys
sys.path.insert(0, "..")

from rtlgen import SinglePortRAM, SimpleDualPortRAM, VerilogEmitter


spram = SinglePortRAM(width=32, depth=1024, name="SPRAM")
sdpram = SimpleDualPortRAM(width=64, depth=512, name="SDPRAM", init_file="data.hex")

if __name__ == "__main__":
    emitter = VerilogEmitter()
    print("// ===== SinglePortRAM =====")
    print(emitter.emit(spram))
    print()
    print("// ===== SimpleDualPortRAM =====")
    print(emitter.emit(sdpram))
