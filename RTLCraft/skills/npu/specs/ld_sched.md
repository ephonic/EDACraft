# ld_sched

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
- `input [1] i_ld_minst_wr_en`
- `output [1] o_ld_minst_wr_rdy`
- `input [MIW_LD-1:0] i_ld_minst_wr_din`
- `input [1] i_ld_uinst_rd_en`
- `output [1] o_ld_uinst_rd_rdy`
- `output [UIW_LD-1:0] o_ld_uinst_rd_dout`
- `input [1] clk`

## FSM States
- `LD_SCHED_INIT` = 0
- `LD_SCHED_ISSUE` = 1

## Logic Block Types
- comb
- seq
