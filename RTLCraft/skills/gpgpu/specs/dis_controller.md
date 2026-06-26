# dis_controller

## Parameters
- `NUMBER_CU = 2`
- `CU_ID_WIDTH = 2`
- `RES_TABLE_ADDR_WIDTH = 1`
- `NUMBER_RES_TABLE = 1 << RES_TABLE_ADDR_WIDTH`
- `ALLOC_NUM_STATES = 'h4`
- `ST_AL_IDLE = 4'h0`

## Ports (20)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] inflight_wg_buffer_alloc_valid_i`
- `input [1] inflight_wg_buffer_alloc_available_i`
- `input [1] allocator_cu_valid_i`
- `input [1] allocator_cu_rejected_i`
- `input [CU_ID_WIDTH-1:0] allocator_cu_id_out_i`
- `input [1] grt_wg_alloc_done_i`
- `input [1] grt_wg_dealloc_done_i`
- `input [CU_ID_WIDTH-1:0] grt_wg_alloc_cu_id_i`
- `input [CU_ID_WIDTH-1:0] grt_wg_dealloc_cu_id_i`
- `input [1] gpu_interface_alloc_available_i`
- `input [1] gpu_interface_dealloc_available_i`
- `input [CU_ID_WIDTH-1:0] gpu_interface_cu_id_i`
- `output [1] dis_controller_start_alloc_o`
- `output [1] dis_controller_alloc_ack_o`
- `output [1] dis_controller_wg_alloc_valid_o`
- `output [1] dis_controller_wg_dealloc_valid_o`
- `output [1] dis_controller_wg_rejected_valid_o`
- `output [NUMBER_CU-1:0] dis_controller_cu_busy_o`

## Logic Block Types
- seq_async_reset
