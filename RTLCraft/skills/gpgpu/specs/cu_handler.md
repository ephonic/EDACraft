# cu_handler

## Ports (14)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] wg_alloc_en_i`
- `input [`WG_ID_WIDTH-1:0] wg_alloc_wg_id_i`
- `input [`WF_COUNT_WIDTH_PER_WG-1:0] wg_alloc_wf_count_i`
- `input [1] ready_for_dispatch2cu_i`
- `input [1] cu2dispatch_wf_done_i`
- `input [`TAG_WIDTH-1:0] cu2dispatch_wf_tag_done_i`
- `input [1] wg_done_ack_i`
- `output [1] dispatch2cu_wf_dispatch_o`
- `output [`TAG_WIDTH-1:0] dispatch2cu_wf_tag_dispatch_o`
- `output [1] wg_done_valid_o`
- `output [`WG_ID_WIDTH-1:0] wg_done_wg_id_o`
- `output [1] invalid_due_to_not_ready_o`

## FSM States
- `TAG_WF_COUNT_L` = 0
- `INFO_RAM_WG_COUNT_L` = 1
- `ST_ALLOC_IDLE` = 2
- `ST_ALLOCATING` = 3
- `ST_DEALLOC_IDLE` = 4
- `ST_DEALLOC_READ_RAM` = 5
- `ST_DEALLOC_PROPAGATE` = 6

## Submodule Instances
- `U_fixed_pri_arb`
- `U_one2bin`
- `U_fixed_pri_arb2`
- `U_one2bin2`

## Logic Block Types
- seq_async_reset
