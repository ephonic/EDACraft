# top_sched

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
- `INST_DEPTH = `INST_DEPTH`
- `INST_ADDRW = `INST_ADDRW`
- `CACHELINE_SIZE = `CACHELINE_SIZE`
- `MDATA_SIZE = `MDATA_SIZE`

## Ports (22)
- `input [1] i_minst_chain_wr_en`
- `input [INST_ADDRW-1:0] i_minst_chain_wr_addr`
- `input [MICW-1:0] i_minst_chain_wr_din`
- `input [1] i_mvu_minst_rd_en`
- `output [1] o_mvu_minst_rd_rdy`
- `output [MIW_MVU-1:0] o_mvu_minst_rd_dout`
- `input [1] i_evrf_minst_rd_en`
- `output [1] o_evrf_minst_rd_rdy`
- `output [MIW_EVRF-1:0] o_evrf_minst_rd_dout`
- `input [1] i_mfu0_minst_rd_en`
- `output [1] o_mfu0_minst_rd_rdy`
- `output [MIW_MFU-1:0] o_mfu0_minst_rd_dout`
- `input [1] i_mfu1_minst_rd_en`
- `output [1] o_mfu1_minst_rd_rdy`
- `output [MIW_MFU-1:0] o_mfu1_minst_rd_dout`
- `input [1] i_ld_minst_rd_en`
- `output [1] o_ld_minst_rd_rdy`
- `output [MIW_LD-1:0] o_ld_minst_rd_dout`
- `input [1] i_start`
- `input [INST_ADDRW-1:0] pc_start_offset`
- `input [1] clk`
- `input [1] rst`

## Logic Block Types
- comb
- seq
