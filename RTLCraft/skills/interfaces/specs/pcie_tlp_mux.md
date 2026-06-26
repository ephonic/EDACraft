# pcie_tlp_mux

## Parameters
- `PORTS = 2`
- `TLP_DATA_WIDTH = 256`
- `TLP_STRB_WIDTH = TLP_DATA_WIDTH/32`
- `TLP_HDR_WIDTH = 128`
- `SEQ_NUM_WIDTH = 6`
- `TLP_SEG_COUNT = 1`
- `ARB_TYPE_ROUND_ROBIN = 0`
- `ARB_LSB_HIGH_PRIORITY = 1`
- `CL_PORTS = $clog2(PORTS)`
- `TLP_SEG_DATA_WIDTH = TLP_DATA_WIDTH / TLP_SEG_COUNT`
- `TLP_SEG_STRB_WIDTH = TLP_STRB_WIDTH / TLP_SEG_COUNT`
- `SEG_SEL_WIDTH = $clog2(TLP_SEG_COUNT)`

## Ports (27)
- `input [1] clk`
- `input [1] rst`
- `input [PORTS*TLP_DATA_WIDTH-1:0] in_tlp_data`
- `input [PORTS*TLP_STRB_WIDTH-1:0] in_tlp_strb`
- `input [PORTS*TLP_SEG_COUNT*TLP_HDR_WIDTH-1:0] in_tlp_hdr`
- `input [PORTS*TLP_SEG_COUNT*SEQ_NUM_WIDTH-1:0] in_tlp_seq`
- `input [PORTS*TLP_SEG_COUNT*3-1:0] in_tlp_bar_id`
- `input [PORTS*TLP_SEG_COUNT*8-1:0] in_tlp_func_num`
- `input [PORTS*TLP_SEG_COUNT*4-1:0] in_tlp_error`
- `input [PORTS*TLP_SEG_COUNT-1:0] in_tlp_valid`
- `input [PORTS*TLP_SEG_COUNT-1:0] in_tlp_sop`
- `input [PORTS*TLP_SEG_COUNT-1:0] in_tlp_eop`
- `output [PORTS-1:0] in_tlp_ready`
- `output [TLP_DATA_WIDTH-1:0] out_tlp_data`
- `output [TLP_STRB_WIDTH-1:0] out_tlp_strb`
- `output [TLP_SEG_COUNT*TLP_HDR_WIDTH-1:0] out_tlp_hdr`
- `output [TLP_SEG_COUNT*SEQ_NUM_WIDTH-1:0] out_tlp_seq`
- `output [TLP_SEG_COUNT*3-1:0] out_tlp_bar_id`
- `output [TLP_SEG_COUNT*8-1:0] out_tlp_func_num`
- `output [TLP_SEG_COUNT*4-1:0] out_tlp_error`
- `output [TLP_SEG_COUNT-1:0] out_tlp_valid`
- `output [TLP_SEG_COUNT-1:0] out_tlp_sop`
- `output [TLP_SEG_COUNT-1:0] out_tlp_eop`
- `input [1] out_tlp_ready`
- `input [PORTS-1:0] pause`
- `output [PORTS*TLP_SEG_COUNT*SEQ_NUM_WIDTH-1:0] sel_tlp_seq`
- `output [PORTS*TLP_SEG_COUNT-1:0] sel_tlp_seq_valid`

## Logic Block Types
- seq
