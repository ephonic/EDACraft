# pcie_tlp_fifo

## Parameters
- `DEPTH = 2048`
- `TLP_DATA_WIDTH = 256`
- `TLP_STRB_WIDTH = TLP_DATA_WIDTH/32`
- `TLP_HDR_WIDTH = 128`
- `SEQ_NUM_WIDTH = 6`
- `IN_TLP_SEG_COUNT = 1`
- `OUT_TLP_SEG_COUNT = IN_TLP_SEG_COUNT`
- `WATERMARK = DEPTH/2`
- `INT_TLP_SEG_COUNT = IN_TLP_SEG_COUNT > OUT_TLP_SEG_COUNT ? IN_TLP_SEG_COUNT : OUT_TLP_SEG_COUNT`
- `IN_TLP_SEG_DATA_WIDTH = TLP_DATA_WIDTH / IN_TLP_SEG_COUNT`
- `IN_TLP_SEG_STRB_WIDTH = TLP_STRB_WIDTH / IN_TLP_SEG_COUNT`
- `INT_TLP_SEG_DATA_WIDTH = TLP_DATA_WIDTH / INT_TLP_SEG_COUNT`
- `INT_TLP_SEG_STRB_WIDTH = TLP_STRB_WIDTH / INT_TLP_SEG_COUNT`
- `OUT_TLP_SEG_DATA_WIDTH = TLP_DATA_WIDTH / OUT_TLP_SEG_COUNT`
- `OUT_TLP_SEG_STRB_WIDTH = TLP_STRB_WIDTH / OUT_TLP_SEG_COUNT`
- `SEG_RATIO = INT_TLP_SEG_COUNT / OUT_TLP_SEG_COUNT`
- `SEG_SEL_WIDTH = $clog2(INT_TLP_SEG_COUNT)`
- `OUTPUT_FIFO_ADDR_WIDTH = 5`

## Ports (26)
- `input [1] clk`
- `input [1] rst`
- `input [TLP_DATA_WIDTH-1:0] in_tlp_data`
- `input [TLP_STRB_WIDTH-1:0] in_tlp_strb`
- `input [IN_TLP_SEG_COUNT*TLP_HDR_WIDTH-1:0] in_tlp_hdr`
- `input [IN_TLP_SEG_COUNT*SEQ_NUM_WIDTH-1:0] in_tlp_seq`
- `input [IN_TLP_SEG_COUNT*3-1:0] in_tlp_bar_id`
- `input [IN_TLP_SEG_COUNT*8-1:0] in_tlp_func_num`
- `input [IN_TLP_SEG_COUNT*4-1:0] in_tlp_error`
- `input [IN_TLP_SEG_COUNT-1:0] in_tlp_valid`
- `input [IN_TLP_SEG_COUNT-1:0] in_tlp_sop`
- `input [IN_TLP_SEG_COUNT-1:0] in_tlp_eop`
- `output [1] in_tlp_ready`
- `output [TLP_DATA_WIDTH-1:0] out_tlp_data`
- `output [TLP_STRB_WIDTH-1:0] out_tlp_strb`
- `output [OUT_TLP_SEG_COUNT*TLP_HDR_WIDTH-1:0] out_tlp_hdr`
- `output [OUT_TLP_SEG_COUNT*SEQ_NUM_WIDTH-1:0] out_tlp_seq`
- `output [OUT_TLP_SEG_COUNT*3-1:0] out_tlp_bar_id`
- `output [OUT_TLP_SEG_COUNT*8-1:0] out_tlp_func_num`
- `output [OUT_TLP_SEG_COUNT*4-1:0] out_tlp_error`
- `output [OUT_TLP_SEG_COUNT-1:0] out_tlp_valid`
- `output [OUT_TLP_SEG_COUNT-1:0] out_tlp_sop`
- `output [OUT_TLP_SEG_COUNT-1:0] out_tlp_eop`
- `input [1] out_tlp_ready`
- `output [1] half_full`
- `output [1] watermark`

## Logic Block Types
- seq
