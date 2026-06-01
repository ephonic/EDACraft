# loader

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
- `NSIZE = `NSIZE`
- `NSIZEW = `NSIZEW`
- `NTAG = `NTAG`
- `NTAGW = `NTAGW`
- `IW = `UIW_LD`
- `QDEPTH = `QDEPTH`
- `WB_LMT = `WB_LMT`
- `WB_LMTW = `WB_LMTW`
- `SIM_FLAG = `SIM_FLAG`
- `INPUT_BUFFER_SIZE = `INPUT_BUFFER_SIZE`
- `OUTPUT_BUFFER_SIZE = `OUTPUT_BUFFER_SIZE`

## Ports (8)
- `output [1] o_vrf_wr_en`
- `output [2*NVRF-1:0] o_vrf_wr_id`
- `output [VRFAW-1:0] o_vrf0_wr_addr`
- `output [VRFAW-1:0] o_vrf1_wr_addr`
- `output [ACCW*DOTW-1:0] o_vrf_wr_data`
- `input [1] i_in_wr_en`
- `output [1] o_in_wr_rdy`
- `input [EW*DOTW-1:0] i_in_wr_din`

## FSM States
- `FROM_IN` = 0
- `FROM_WB` = 1
- `LD_PIPELINE` = 2
- `TREE_LVLS` = 3
- `FORK_FACTOR_0` = 4
- `FORK_FACTOR_1` = 5
- `FORK_FACTOR_2` = 6
- `EMIT_MVU` = 7
- `EMIT_MFU_0` = 8
- `EMIT_MFU_1` = 9
- `EMIT_OUT_VEC` = 10

## Logic Block Types
- seq
