# wg_slot_id_convert_opt

## Parameters
- `NUMBER_CU = 2`
- `CU_ID_WIDTH = 1`

## Ports (8)
- `input [1] clk`
- `input [1] rst_n`
- `input [`WG_ID_WIDTH-1:0] wg_id_i`
- `input [CU_ID_WIDTH-1:0] cu_id_i`
- `input [1] find_and_cancel_i`
- `input [1] generate_i`
- `output [`WG_SLOT_ID_WIDTH-1:0] wg_slot_id_gen_o`
- `output [`WG_SLOT_ID_WIDTH-1:0] wg_slot_id_find_o`

## FSM States
- `SLOT_ID_NUM` = 0

## Submodule Instances
- `U_fixed_pri_arb`
- `U_one2bin`
- `U_one2bin_1`

## Logic Block Types
- seq_async_reset
