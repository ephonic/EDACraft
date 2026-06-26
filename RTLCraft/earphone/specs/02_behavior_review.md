# 02 Behavior Review

- RV32IM ISS: architectural state = x0-x31, pc, memory.
- SIMD16: per-lane INT16 ops, predicate mask, FP16 MAC.
- FFT256: DFT with 1/N scaling per stage.
- QSPI: XIP read transaction = cmd + addr + dummy + data.
- I2C: START + 7-bit addr + R/W + byte + ACK + STOP.
- SRAM: single-cycle APB read/write with byte strobe.
- APBBridge: address decode into 1 MB regions.
