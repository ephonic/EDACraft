# self_tester_shim

## Parameters
- `NUM_INPUTS = `NUM_INPUTS`
- `INPUT_WIDTH = `DOTW * `EW`
- `INPUT_MIF_FILE = {`RTL_DIR`
- `INPUT_ADDRW = $clog2(NUM_INPUTS)`
- `NUM_OUTPUTS = `NUM_OUTPUTS`
- `OUTPUT_WIDTH = `DOTW * `ACCW`
- `OUTPUT_LOWER_MIF_FILE = {`RTL_DIR`
- `OUTPUT_UPPER_MIF_FILE = {`RTL_DIR`
- `OUTPUT_ADDRW = $clog2(NUM_OUTPUTS)`
- `OR_TREE_PADDING = (2 ** $clog2(OUTPUT_WIDTH))-OUTPUT_WIDTH`
- `OUTPUT_BUFFER_SIZE = `OUTPUT_BUFFER_SIZE`
- `INST_DEPTH = `INST_DEPTH`
- `INST_ADDRW = `INST_ADDRW`
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
- `DW = 1024`

## Ports (6)
- `input [1] clk`
- `input [1] rst`
- `input [DW-1:0] din`
- `input [1] valid_in`
- `output [1] result`
- `output [1] valid_out`

## Logic Block Types
- seq
