# pcie_tlp_fc_count

## Parameters
- `TLP_HDR_WIDTH = 128`
- `TLP_SEG_COUNT = 1`

## Ports (12)
- `input [1] clk`
- `input [1] rst`
- `input [TLP_SEG_COUNT*TLP_HDR_WIDTH-1:0] tlp_hdr`
- `input [TLP_SEG_COUNT-1:0] tlp_valid`
- `input [TLP_SEG_COUNT-1:0] tlp_sop`
- `input [1] tlp_ready`
- `output [3:0] out_fc_ph`
- `output [8:0] out_fc_pd`
- `output [3:0] out_fc_nph`
- `output [8:0] out_fc_npd`
- `output [3:0] out_fc_cplh`
- `output [8:0] out_fc_cpld`

## Logic Block Types
- seq
