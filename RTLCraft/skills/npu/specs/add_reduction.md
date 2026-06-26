# add_reduction

## Parameters
- `EW = 16`
- `DOTW = 400`
- `NTILE = 6`
- `EW = `EW`
- `ACCW = `ACCW`
- `DOTW = `DOTW`
- `NTILE = `NTILE`
- `NDPE = `NDPE`
- `NMFU = `NMFU`
- `NVRF = `NVRF`
- `NMRF = `NMRF`
- `VRFD = `VRFD`
- `VRFAW = `VRFAW`
- `MRFD = `MRFD`
- `MRFAW = `MRFAW`
- `MRFIDW = `MRFIDW`
- `NSIZE = `NSIZE`
- `NSIZEW = `NSIZEW`
- `NTAG = `NTAG`
- `NTAGW = `NTAGW`
- `PRIME_DOTW = `PRIME_DOTW`
- `DOT_PER_DSP = `DOT_PER_DSP`
- `NUM_DSP = `NUM_DSP`
- `NUM_ACCUM = `NUM_ACCUM`
- `ACCIDW = `ACCIDW`
- `VRFIDW = `VRFIDW`
- `IW = `UIW_MVU`
- `QDEPTH = `QDEPTH`
- `CREDITW = $clog2(QDEPTH)`
- `WB_LMT = `WB_LMT`
- `WB_LMTW = `WB_LMTW`
- `TILES_THRESHOLD = `TILES_THRESHOLD`
- `DPES_THRESHOLD = `DPES_THRESHOLD`
- `SIM_FLAG = `SIM_FLAG`
- `TARGET_FPGA = `TARGET_FPGA`

## Ports (5)
- `input [NTILE*EW*DOTW-1:0] din`
- `input [1] valid_in`
- `output [EW*DOTW-1:0] dout`
- `output [1] valid_out`
- `input [1] clk`

## FSM States
- `TILE_CHAIN_LATENCY` = 0
- `ACCUM_TO_OFIFO` = 1
- `TILE_TO_ACCUM` = 2
- `RESET_DELAY` = 3

## Logic Block Types
- seq
