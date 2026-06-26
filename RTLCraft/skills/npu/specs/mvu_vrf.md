# mvu_vrf

## Parameters
- `MODULE_ID = ""`
- `OUTREG = "CLOCK0"`
- `ID = 0`
- `DW = 32`
- `DEPTH = 512`
- `AW = 9`
- `RTL_DIR = `RTL_DIR`
- `TARGET_FPGA = `TARGET_FPGA`
- `EW = `EW`
- `DEVICE = (TARGET_FPGA == "S10-Prime")? "Stratix 10": TARGET_FPGA`
- `PRIME_DOTW = `PRIME_DOTW`
- `DOTW = `DOTW`
- `NUM_DSP = `NUM_DSP`
- `NUM_RAM = (TARGET_FPGA == "S10-Prime")? NUM_DSP: 1`
- `RW = DW / NUM_RAM`
- `VRFIDW = `VRFIDW`
- `MVU_TILE = 0`

## Logic Block Types
- seq
