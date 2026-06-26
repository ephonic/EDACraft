# scalar_regfile_bank

## Ports (8)
- `input [1] clk`
- `input [1] rst_n`
- `input [`DEPTH_REGBANK-1:0] rsidx_i`
- `input [1] rsren_i`
- `input [`XLEN-1:0] rd_i`
- `input [`DEPTH_REGBANK-1:0] rdidx_i`
- `input [1] rdwen_i`
- `output [`XLEN-1:0] rs_o`

## Submodule Instances
- `U_GPGPU_RF_2P_256X32M_0`
- `SRAM`
