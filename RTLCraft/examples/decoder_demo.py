#!/usr/bin/env python3
"""译码器/编码器示例。"""

import sys
sys.path.insert(0, "..")

from rtlgen import Decoder, PriorityEncoder, VerilogEmitter


dec = Decoder(in_width=3)
enc = PriorityEncoder(in_width=8)

if __name__ == "__main__":
    emitter = VerilogEmitter()
    print("// ===== Decoder =====")
    print(emitter.emit(dec))
    print()
    print("// ===== PriorityEncoder =====")
    print(emitter.emit(enc))
