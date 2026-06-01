# mvu_tile

## Parameters
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
- `DOT_PER_DSP = `DOT_PER_DSP`
- `PRIME_DOTW = `PRIME_DOTW`
- `PDOTW = `PRIME_DOTW`
- `NUM_DSP = `NUM_DSP`
- `NUM_ACCUM = `NUM_ACCUM`
- `ACCIDW = `ACCIDW`
- `VRFIDW = `VRFIDW`
- `IW = `UIW_MVU`
- `QDEPTH = `QDEPTH`
- `WB_LMT = `WB_LMT`
- `WB_LMTW = `WB_LMTW`
- `MULT_LATENCY = `MULT_LATENCY`
- `DPE_PIPELINE = `DPE_PIPELINE`
- `SIM_FLAG = `SIM_FLAG`
- `HARD_TILE = 1`
- `DPES_THRESHOLD = `DPES_THRESHOLD`
- `PRECISION = `PRECISION`
- `BRAM_RD_LATENCY = `BRAM_RD_LATENCY`
- `MVU_TILE_ID = 0`
- `VRF0_ID = MVU_TILE_ID`
- `TARGET_FPGA = `TARGET_FPGA`
- `NUM_CHUNKS = NDPE/DOTW`

## Ports (24)
- `input [1] clk`
- `input [1] rst`
- `input [MRFAW-1:0] i_mrf_wr_addr`
- `input [EW*DOTW-1:0] i_mrf_wr_data`
- `input [MRFIDW-1:0] i_mrf_wr_en`
- `input [VRFAW-1:0] i_vrf0_wr_addr`
- `input [VRFAW-1:0] i_vrf1_wr_addr`
- `input [EW*DOTW-1:0] i_vrf_wr_data`
- `input [1] i_vrf_wr_en`
- `input [2*NVRF-1:0] i_vrf_wr_id`
- `input [VRFAW-1:0] i_vrf0_wr_addr1`
- `input [VRFAW-1:0] i_vrf1_wr_addr1`
- `input [EW*DOTW-1:0] i_vrf_wr_data1`
- `input [1] i_vrf_wr_en1`
- `input [2*NVRF-1:0] i_vrf_wr_id1`
- `input [IW-1:0] i_inst`
- `input [1] i_inst_valid`
- `input [3*ACCW*NDPE-1:0] i_from_prev_tile`
- `output [3*ACCW*NDPE-1:0] o_to_next_tile`
- `input [3*ACCW*NDPE-1:0] i_from_prev_tile1`
- `output [3*ACCW*NDPE-1:0] o_to_next_tile1`
- `output [1] o_valid`
- `output [1:0] o_accum_op`
- `output [ACCIDW-1:0] o_accum_sel`

## FSM States
- `RESET_DELAY` = 0
- `TREE_LVLS` = 1
- `FORK_FACTOR_0` = 2

## Logic Block Types
- seq
