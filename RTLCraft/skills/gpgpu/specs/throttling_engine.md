# throttling_engine

## Parameters
- `NUMBER_CU = 2`
- `CU_ID_WIDTH = 1`

## Ports (10)
- `input [1] clk`
- `input [1] rst_n`
- `input [CU_ID_WIDTH-1:0] cu_id_i`
- `input [1] alloc_en_i`
- `input [1] dealloc_en_i`
- `input [`WG_SLOT_ID_WIDTH:0] wg_max_update_i`
- `input [1] wg_max_update_valid_i`
- `input [1] wg_max_update_all_cu_i`
- `input [CU_ID_WIDTH-1:0] wg_max_update_cu_id_i`
- `output [`WG_SLOT_ID_WIDTH:0] wg_count_available_o`

## Logic Block Types
- seq_async_reset
