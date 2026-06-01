# vector_regfile_bank

## Ports (10)
- `input [1] clk`
- `input [1] rst_n`
- `input [`DEPTH_REGBANK-1:0] rsidx_i`
- `input [1] rsren_i`
- `input [`XLEN*`NUM_THREAD-1:0] rd_i`
- `input [`DEPTH_REGBANK-1:0] rdidx_i`
- `input [1] rdwen_i`
- `input [`NUM_THREAD-1:0] rdwmask_i`
- `output [`XLEN*`NUM_THREAD-1:0] rs_o`
- `output [`XLEN*`NUM_THREAD-1:0] v0_o`

## Submodule Instances
- `U_GPGPU_RF_2P_256X128M_0`
- `U_GPGPU_RF_2P_256X128M_1`
- `U_GPGPU_RF_2P_256X128M_2`
- `U_GPGPU_RF_2P_256X128M_3`
- `U_GPGPU_RF_2P_256X128M_4`
- `U_GPGPU_RF_2P_256X128M_5`
- `U_GPGPU_RF_2P_256X128M_6`
- `U_GPGPU_RF_2P_256X128M_7`
- `SRAM`

## Logic Block Types
- comb
- seq_async_reset
