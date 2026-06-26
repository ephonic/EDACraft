# evrf_sched

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
- `DOT_PER_DSP = `DOT_PER_DSP`
- `PRIME_DOTW = `PRIME_DOTW`
- `NUM_DSP = `NUM_DSP`
- `NUM_ACCUM = `NUM_ACCUM`
- `ACCIDW = `ACCIDW`
- `VRFIDW = `VRFIDW`
- `MIW_MVU = `MIW_MVU`
- `UIW_MVU = `UIW_MVU`
- `MIW_EVRF = `MIW_EVRF`
- `UIW_EVRF = `UIW_EVRF`
- `MIW_MFU = `MIW_MFU`
- `UIW_MFU = `UIW_MFU`
- `MIW_LD = `MIW_LD`
- `UIW_LD = `UIW_LD`
- `MICW = `MICW`
- `QDEPTH = `QDEPTH`
- `WB_LMT = `WB_LMT`
- `WB_LMTW = `WB_LMTW`

## Ports (7)
- `input [1] i_evrf_minst_wr_en`
- `output [1] o_evrf_minst_wr_rdy`
- `input [MIW_EVRF-1:0] i_evrf_minst_wr_din`
- `input [1] i_evrf_uinst_rd_en`
- `output [1] o_evrf_uinst_rd_rdy`
- `output [UIW_EVRF-1:0] o_evrf_uinst_rd_dout`
- `input [1] clk`

## FSM States
- `EVRF_SCHED_INIT` = 0
- `EVRF_SCHED_ISSUE` = 1
- `EVRF_SCHED_LOOP` = 2
- `FROM_MVU` = 3
- `FROM_VRF` = 4
- `FLUSH_MVU` = 5
- `COUNTW` = 6

## Logic Block Types
- comb
- seq
