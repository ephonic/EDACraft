# mac_pause_ctrl_tx

## Parameters
- `MCF_PARAMS_SIZE = 18`
- `PFC_ENABLE = 1`

## Ports (37)
- `input [1] clk`
- `input [1] rst`
- `output [1] mcf_valid`
- `input [1] mcf_ready`
- `output [47:0] mcf_eth_dst`
- `output [47:0] mcf_eth_src`
- `output [15:0] mcf_eth_type`
- `output [15:0] mcf_opcode`
- `output [MCF_PARAMS_SIZE*8-1:0] mcf_params`
- `input [1] tx_lfc_req`
- `input [1] tx_lfc_resend`
- `input [7:0] tx_pfc_req`
- `input [1] tx_pfc_resend`
- `input [47:0] cfg_tx_lfc_eth_dst`
- `input [47:0] cfg_tx_lfc_eth_src`
- `input [15:0] cfg_tx_lfc_eth_type`
- `input [15:0] cfg_tx_lfc_opcode`
- `input [1] cfg_tx_lfc_en`
- `input [15:0] cfg_tx_lfc_quanta`
- `input [15:0] cfg_tx_lfc_refresh`
- `input [47:0] cfg_tx_pfc_eth_dst`
- `input [47:0] cfg_tx_pfc_eth_src`
- `input [15:0] cfg_tx_pfc_eth_type`
- `input [15:0] cfg_tx_pfc_opcode`
- `input [1] cfg_tx_pfc_en`
- `input [8*16-1:0] cfg_tx_pfc_quanta`
- `input [8*16-1:0] cfg_tx_pfc_refresh`
- `input [9:0] cfg_quanta_step`
- `input [1] cfg_quanta_clk_en`
- `output [1] stat_tx_lfc_pkt`
- `output [1] stat_tx_lfc_xon`
- `output [1] stat_tx_lfc_xoff`
- `output [1] stat_tx_lfc_paused`
- `output [1] stat_tx_pfc_pkt`
- `output [7:0] stat_tx_pfc_xon`
- `output [7:0] stat_tx_pfc_xoff`
- `output [7:0] stat_tx_pfc_paused`

## FSM States
- `QFB` = 0

## Logic Block Types
- seq
