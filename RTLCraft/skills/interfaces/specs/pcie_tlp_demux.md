# pcie_tlp_demux

## Parameters
- `PORTS = 2`
- `TLP_DATA_WIDTH = 256`
- `TLP_STRB_WIDTH = TLP_DATA_WIDTH/32`
- `TLP_HDR_WIDTH = 128`
- `SEQ_NUM_WIDTH = 6`
- `IN_TLP_SEG_COUNT = 1`
- `OUT_TLP_SEG_COUNT = IN_TLP_SEG_COUNT`
- `FIFO_ENABLE = 1`
- `FIFO_DEPTH = 2048`
- `FIFO_WATERMARK = FIFO_DEPTH/2`
- `CL_PORTS = $clog2(PORTS)`
- `TLP_SEG_DATA_WIDTH = TLP_DATA_WIDTH / IN_TLP_SEG_COUNT`
- `TLP_SEG_STRB_WIDTH = TLP_STRB_WIDTH / IN_TLP_SEG_COUNT`
- `SEG_SEL_WIDTH = $clog2(IN_TLP_SEG_COUNT)`

## Ports (32)
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
- `output [PORTS*TLP_DATA_WIDTH-1:0] out_tlp_data`
- `output [PORTS*TLP_STRB_WIDTH-1:0] out_tlp_strb`
- `output [PORTS*OUT_TLP_SEG_COUNT*TLP_HDR_WIDTH-1:0] out_tlp_hdr`
- `output [PORTS*OUT_TLP_SEG_COUNT*SEQ_NUM_WIDTH-1:0] out_tlp_seq`
- `output [PORTS*OUT_TLP_SEG_COUNT*3-1:0] out_tlp_bar_id`
- `output [PORTS*OUT_TLP_SEG_COUNT*8-1:0] out_tlp_func_num`
- `output [PORTS*OUT_TLP_SEG_COUNT*4-1:0] out_tlp_error`
- `output [PORTS*OUT_TLP_SEG_COUNT-1:0] out_tlp_valid`
- `output [PORTS*OUT_TLP_SEG_COUNT-1:0] out_tlp_sop`
- `output [PORTS*OUT_TLP_SEG_COUNT-1:0] out_tlp_eop`
- `input [PORTS-1:0] out_tlp_ready`
- `output [IN_TLP_SEG_COUNT*TLP_HDR_WIDTH-1:0] match_tlp_hdr`
- `output [IN_TLP_SEG_COUNT*3-1:0] match_tlp_bar_id`
- `output [IN_TLP_SEG_COUNT*8-1:0] match_tlp_func_num`
- `input [1] enable`
- `input [IN_TLP_SEG_COUNT-1:0] drop`
- `input [PORTS*IN_TLP_SEG_COUNT-1:0] select`
- `output [PORTS-1:0] fifo_half_full`
- `output [PORTS-1:0] fifo_watermark`

## Logic Block Types
- seq
