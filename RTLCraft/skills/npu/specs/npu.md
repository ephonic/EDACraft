# npu

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
- `MULT_LATENCY = `MULT_LATENCY`
- `DPE_PIPELINE = `DPE_PIPELINE`
- `SIM_FLAG = `SIM_FLAG`
- `TILES_THRESHOLD = `TILES_THRESHOLD`
- `DPES_THRESHOLD = `DPES_THRESHOLD`
- `RTL_DIR = `RTL_DIR`
- `TARGET_FPGA = `TARGET_FPGA`
- `INPUT_BUFFER_SIZE = `INPUT_BUFFER_SIZE`
- `OUTPUT_BUFFER_SIZE = `OUTPUT_BUFFER_SIZE`
- `INST_DEPTH = `INST_DEPTH`
- `INST_ADDRW = `INST_ADDRW`

## Ports (6)
- `input [1] i_minst_chain_wr_en`
- `input [MICW-1:0] i_minst_chain_wr_din`
- `input [INST_ADDRW-1:0] i_minst_chain_wr_addr`
- `input [1] i_ld_in_wr_en`
- `output [1] o_ld_in_wr_rdy`
- `input [EW*DOTW-1:0] i_ld_in_wr_din`

## FSM States
- `RESET_ENDPOINTS` = 0
- `RESET_DELAY` = 1
