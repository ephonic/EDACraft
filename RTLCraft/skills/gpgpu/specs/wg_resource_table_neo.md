# wg_resource_table_neo

## Parameters
- `NUMBER_CU = 2`
- `CU_ID_WIDTH = 1`

## Ports (9)
- `input [1] clk`
- `input [1] rst_n`
- `input [CU_ID_WIDTH-1:0] cu_id_i`
- `input [1] alloc_en_i`
- `input [1] dealloc_en_i`
- `input [`WF_COUNT_WIDTH_PER_WG-1:0] wf_count_i`
- `input [`WG_SLOT_ID_WIDTH-1:0] alloc_wg_slot_id_i`
- `input [`WG_SLOT_ID_WIDTH-1:0] dealloc_wg_slot_id_i`
- `output [`WF_COUNT_WIDTH-1:0] wf_count_o`

## FSM States
- `SLOT_ID_NUM` = 0

## Logic Block Types
- seq_async_reset
