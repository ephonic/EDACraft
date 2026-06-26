# resource_table_group

## Parameters
- `NUMBER_CU = 2`

## Ports (23)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] alloc_en_i`
- `input [1] dealloc_en_i`
- `input [`WG_ID_WIDTH-1:0] wg_id_i`
- `input [`CU_ID_WIDTH-`RES_TABLE_ADDR_WIDTH-1:0] sub_cu_id_i`
- `input [`LDS_ID_WIDTH-1:0] lds_start_i`
- `input [`LDS_ID_WIDTH:0] lds_size_i`
- `input [`VGPR_ID_WIDTH-1:0] vgpr_start_i`
- `input [`VGPR_ID_WIDTH:0] vgpr_size_i`
- `input [`SGPR_ID_WIDTH-1:0] sgpr_start_i`
- `input [`SGPR_ID_WIDTH:0] sgpr_size_i`
- `input [`WF_COUNT_WIDTH_PER_WG-1:0] wf_count_i`
- `input [1] done_cancelled_i`
- `output [1] res_tbl_done_o`
- `output [`LDS_ID_WIDTH-1:0] lds_start_o`
- `output [`LDS_ID_WIDTH:0] lds_size_o`
- `output [`VGPR_ID_WIDTH-1:0] vgpr_start_o`
- `output [`VGPR_ID_WIDTH:0] vgpr_size_o`
- `output [`SGPR_ID_WIDTH-1:0] sgpr_start_o`
- `output [`SGPR_ID_WIDTH:0] sgpr_size_o`
- `output [`WF_COUNT_WIDTH-1:0] wf_count_o`
- `output [`WG_SLOT_ID_WIDTH:0] wg_count_o`

## Logic Block Types
- seq_async_reset
