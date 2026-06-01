# pcie_tlp_fifo_mux

## Parameters
- `PORTS = 2`
- `TLP_DATA_WIDTH = 256`
- `TLP_STRB_WIDTH = TLP_DATA_WIDTH/32`
- `TLP_HDR_WIDTH = 128`
- `SEQ_NUM_WIDTH = 6`
- `IN_TLP_SEG_COUNT = 1`
- `OUT_TLP_SEG_COUNT = IN_TLP_SEG_COUNT`
- `ARB_TYPE_ROUND_ROBIN = 0`
- `ARB_LSB_HIGH_PRIORITY = 1`
- `FIFO_DEPTH = 2048`
- `FIFO_WATERMARK = FIFO_DEPTH/2`
- `CL_PORTS = $clog2(PORTS)`
- `TLP_SEG_DATA_WIDTH = TLP_DATA_WIDTH / OUT_TLP_SEG_COUNT`
- `TLP_SEG_STRB_WIDTH = TLP_STRB_WIDTH / OUT_TLP_SEG_COUNT`
- `SEG_SEL_WIDTH = $clog2(OUT_TLP_SEG_COUNT)`
- `OUTPUT_FIFO_ADDR_WIDTH = 5`

## Ports (35)
- `input [1] clk`
- `input [1] rst`
- `input [PORTS*TLP_DATA_WIDTH-1:0] in_tlp_data`
- `input [PORTS*TLP_STRB_WIDTH-1:0] in_tlp_strb`
- `input [PORTS*IN_TLP_SEG_COUNT*TLP_HDR_WIDTH-1:0] in_tlp_hdr`
- `input [PORTS*IN_TLP_SEG_COUNT*SEQ_NUM_WIDTH-1:0] in_tlp_seq`
- `input [PORTS*IN_TLP_SEG_COUNT*3-1:0] in_tlp_bar_id`
- `input [PORTS*IN_TLP_SEG_COUNT*8-1:0] in_tlp_func_num`
- `input [PORTS*IN_TLP_SEG_COUNT*4-1:0] in_tlp_error`
- `input [PORTS*IN_TLP_SEG_COUNT-1:0] in_tlp_valid`
- `input [PORTS*IN_TLP_SEG_COUNT-1:0] in_tlp_sop`
- `input [PORTS*IN_TLP_SEG_COUNT-1:0] in_tlp_eop`
- `output [PORTS-1:0] in_tlp_ready`
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
- `output [3:0] out_fc_ph`
- `output [8:0] out_fc_pd`
- `output [3:0] out_fc_nph`
- `output [8:0] out_fc_npd`
- `output [3:0] out_fc_cplh`
- `output [8:0] out_fc_cpld`
- `input [PORTS-1:0] pause`
- `output [PORTS*OUT_TLP_SEG_COUNT*SEQ_NUM_WIDTH-1:0] sel_tlp_seq`
- `output [PORTS*OUT_TLP_SEG_COUNT-1:0] sel_tlp_seq_valid`
- `output [PORTS-1:0] fifo_half_full`
- `output [PORTS-1:0] fifo_watermark`

## Logic Block Types
- seq
