# ram

## Parameters
- `MODULE_ID = ""`
- `OUTREG = "CLOCK0"`
- `ID = 0`
- `ID_UNITS = (ID%10) + 8'h30`
- `ID_TENS = (ID/10 == 0)? "": ((ID/10)%10) + 8'h30`
- `ID_HUNDREDS = (ID/100 == 0)? "": (ID/100) + 8'h30`
- `DW = 32`
- `DEPTH = 512`
- `AW = 9`
- `RTL_DIR = `RTL_DIR`
- `TARGET_FPGA = `TARGET_FPGA`
