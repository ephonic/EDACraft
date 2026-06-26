# mac_pause_ctrl_rx

## Parameters
- `MCF_PARAMS_SIZE = 18`
- `PFC_ENABLE = 1`

## Ports (28)
- `input [1] clk`
- `input [1] rst`
- `input [1] mcf_valid`
- `input [47:0] mcf_eth_dst`
- `input [47:0] mcf_eth_src`
- `input [15:0] mcf_eth_type`
- `input [15:0] mcf_opcode`
- `input [MCF_PARAMS_SIZE*8-1:0] mcf_params`
- `input [1] rx_lfc_en`
- `output [1] rx_lfc_req`
- `input [1] rx_lfc_ack`
- `input [7:0] rx_pfc_en`
- `output [7:0] rx_pfc_req`
- `input [7:0] rx_pfc_ack`
- `input [15:0] cfg_rx_lfc_opcode`
- `input [1] cfg_rx_lfc_en`
- `input [15:0] cfg_rx_pfc_opcode`
- `input [1] cfg_rx_pfc_en`
- `input [9:0] cfg_quanta_step`
- `input [1] cfg_quanta_clk_en`
- `output [1] stat_rx_lfc_pkt`
- `output [1] stat_rx_lfc_xon`
- `output [1] stat_rx_lfc_xoff`
- `output [1] stat_rx_lfc_paused`
- `output [1] stat_rx_pfc_pkt`
- `output [7:0] stat_rx_pfc_xon`
- `output [7:0] stat_rx_pfc_xoff`
- `output [7:0] stat_rx_pfc_paused`

## FSM States
- `QFB` = 0

## Logic Block Types
- seq
