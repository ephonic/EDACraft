# pcie_ed_MEM

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
- `OUTPUT_BUFFER_SIZE = `OUTPUT_BUFFER_SIZE`
- `INST_DEPTH = `INST_DEPTH`
- `INST_ADDRW = `INST_ADDRW`

## Ports (17)
- `input [13:0] address`
- `output [511:0] readdata`
- `input [1] clken`
- `input [1] chipselect`
- `input [1] write`
- `input [511:0] writedata`
- `input [63:0] byteenable`
- `input [13:0] address2`
- `output [511:0] readdata2`
- `input [1] clken2`
- `input [1] chipselect2`
- `input [1] write2`
- `input [511:0] writedata2`
- `input [63:0] byteenable2`
- `input [1] clk`
- `input [1] reset`
- `input [1] reset_req`

## FSM States
- `DMA_ADDR_OFFFSET` = 0
- `DMA_POLL_REG` = 1
- `DMA_SOFT_RST` = 2
- `BUF0_START` = 3

## Logic Block Types
- seq
