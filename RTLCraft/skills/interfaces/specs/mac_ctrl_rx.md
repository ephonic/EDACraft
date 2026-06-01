# mac_ctrl_rx

## Parameters
- `DATA_WIDTH = 8`
- `KEEP_ENABLE = DATA_WIDTH>8`
- `KEEP_WIDTH = DATA_WIDTH/8`
- `ID_ENABLE = 0`
- `ID_WIDTH = 8`
- `DEST_ENABLE = 0`
- `DEST_WIDTH = 8`
- `USER_ENABLE = 1`
- `USER_WIDTH = 1`
- `USE_READY = 0`
- `MCF_PARAMS_SIZE = 18`
- `BYTE_LANES = KEEP_ENABLE ? KEEP_WIDTH : 1`
- `HDR_SIZE = 60`
- `CYCLE_COUNT = (HDR_SIZE+BYTE_LANES-1)/BYTE_LANES`
- `PTR_WIDTH = $clog2(CYCLE_COUNT)`
- `OFFSET = HDR_SIZE % BYTE_LANES`

## Ports (41)
- `input [1] clk`
- `input [1] rst`
- `input [DATA_WIDTH-1:0] s_axis_tdata`
- `input [KEEP_WIDTH-1:0] s_axis_tkeep`
- `input [1] s_axis_tvalid`
- `output [1] s_axis_tready`
- `input [1] s_axis_tlast`
- `input [ID_WIDTH-1:0] s_axis_tid`
- `input [DEST_WIDTH-1:0] s_axis_tdest`
- `input [USER_WIDTH-1:0] s_axis_tuser`
- `output [DATA_WIDTH-1:0] m_axis_tdata`
- `output [KEEP_WIDTH-1:0] m_axis_tkeep`
- `output [1] m_axis_tvalid`
- `input [1] m_axis_tready`
- `output [1] m_axis_tlast`
- `output [ID_WIDTH-1:0] m_axis_tid`
- `output [DEST_WIDTH-1:0] m_axis_tdest`
- `output [USER_WIDTH-1:0] m_axis_tuser`
- `output [1] mcf_valid`
- `output [47:0] mcf_eth_dst`
- `output [47:0] mcf_eth_src`
- `output [15:0] mcf_eth_type`
- `output [15:0] mcf_opcode`
- `output [MCF_PARAMS_SIZE*8-1:0] mcf_params`
- `output [ID_WIDTH-1:0] mcf_id`
- `output [DEST_WIDTH-1:0] mcf_dest`
- `output [USER_WIDTH-1:0] mcf_user`
- `input [47:0] cfg_mcf_rx_eth_dst_mcast`
- `input [1] cfg_mcf_rx_check_eth_dst_mcast`
- `input [47:0] cfg_mcf_rx_eth_dst_ucast`
- `input [1] cfg_mcf_rx_check_eth_dst_ucast`
- `input [47:0] cfg_mcf_rx_eth_src`
- `input [1] cfg_mcf_rx_check_eth_src`
- `input [15:0] cfg_mcf_rx_eth_type`
- `input [15:0] cfg_mcf_rx_opcode_lfc`
- `input [1] cfg_mcf_rx_check_opcode_lfc`
- `input [15:0] cfg_mcf_rx_opcode_pfc`
- `input [1] cfg_mcf_rx_check_opcode_pfc`
- `input [1] cfg_mcf_rx_forward`
- `input [1] cfg_mcf_rx_enable`
- `output [1] stat_rx_mcf`

## Logic Block Types
- seq
