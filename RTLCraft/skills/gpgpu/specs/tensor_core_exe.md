# tensor_core_exe

## Parameters
- `VL = `NUM_THREAD`
- `DIM_M = 2`
- `DIM_N = 2`
- `DIM_K = 2`
- `EXPWIDTH = 8`
- `PRECISION = 24`

## Ports (17)
- `input [1] clk`
- `input [1] rst_n`
- `input [`NUM_THREAD*`XLEN-1:0] in1_i`
- `input [`NUM_THREAD*`XLEN-1:0] in2_i`
- `input [`NUM_THREAD*`XLEN-1:0] in3_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_reg_idxw_i`
- `input [`DEPTH_WARP-1:0] ctrl_wid_i`
- `input [2:0] rm_i`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [`NUM_THREAD*`XLEN-1:0] wb_wvd_rd_o`
- `output [`NUM_THREAD-1:0] wvd_mask_o`
- `output [1] wvd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] reg_idxw_o`
- `output [`DEPTH_WARP-1:0] warp_id_o`

## Submodule Instances
- `U_tensor`
