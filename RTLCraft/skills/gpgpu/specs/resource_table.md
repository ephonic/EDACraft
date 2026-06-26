# resource_table

## Parameters
- `NUMBER_CU = 2`
- `CU_ID_WIDTH = 1`
- `RES_ID_WIDTH = 10`
- `NUMBER_RES_SLOTS = 1024`

## Ports (13)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] alloc_res_en_i`
- `input [1] dealloc_res_en_i`
- `input [CU_ID_WIDTH-1:0] alloc_cu_id_i`
- `input [CU_ID_WIDTH-1:0] dealloc_cu_id_i`
- `input [`WG_SLOT_ID_WIDTH-1:0] alloc_wg_slot_id_i`
- `input [`WG_SLOT_ID_WIDTH-1:0] dealloc_wg_slot_id_i`
- `input [RES_ID_WIDTH:0] alloc_res_size_i`
- `input [RES_ID_WIDTH-1:0] alloc_res_start_i`
- `output [1] res_table_done_o`
- `output [RES_ID_WIDTH:0] cam_biggest_space_size_o`
- `output [RES_ID_WIDTH-1:0] cam_biggest_space_addr_o`

## FSM States
- `TABLE_ENTRY_WIDTH` = 0
- `RES_STRT_L` = 1
- `ST_M_IDLE` = 2
- `ST_M_ALLOC` = 3
- `ST_M_DEALLOC` = 4
- `ST_M_FIND_MAX` = 5
- `ST_A_IDLE` = 6
- `ST_A_FIND_POSITION` = 7
- `ST_A_UPDATE_PREV_ENTRY` = 8
- `ST_A_WRITE_NEW_ENTRY` = 9
- `ST_D_IDLE` = 10
- `ST_D_READ_PREV_ENTRY` = 11
- `ST_D_READ_NEXT_ENTRY` = 12
- `ST_D_UPDATE_PREV_ENTRY` = 13
- `ST_D_UPDATE_NEXT_ENTRY` = 14
- `ST_F_IDLE` = 15
- `ST_F_FIRST_ITEM` = 16
- `ST_F_SEARCHING` = 17
- `ST_F_LAST_ITEM` = 18

## Logic Block Types
- seq_async_reset
