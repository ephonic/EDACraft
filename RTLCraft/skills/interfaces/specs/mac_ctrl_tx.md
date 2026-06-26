# mac_ctrl_tx

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
- `MCF_PARAMS_SIZE = 18`
- `BYTE_LANES = KEEP_ENABLE ? KEEP_WIDTH : 1`
- `HDR_SIZE = 60`
- `CYCLE_COUNT = (HDR_SIZE+BYTE_LANES-1)/BYTE_LANES`
- `PTR_WIDTH = $clog2(CYCLE_COUNT)`
- `OFFSET = HDR_SIZE % BYTE_LANES`

## Ports (31)
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
- `input [1] mcf_valid`
- `output [1] mcf_ready`
- `input [47:0] mcf_eth_dst`
- `input [47:0] mcf_eth_src`
- `input [15:0] mcf_eth_type`
- `input [15:0] mcf_opcode`
- `input [MCF_PARAMS_SIZE*8-1:0] mcf_params`
- `input [ID_WIDTH-1:0] mcf_id`
- `input [DEST_WIDTH-1:0] mcf_dest`
- `input [USER_WIDTH-1:0] mcf_user`
- `input [1] tx_pause_req`
- `output [1] tx_pause_ack`
- `output [1] stat_tx_mcf`

## Logic Block Types
- seq
