# ip_eth_tx_64

## Ports (36)
- `input [1] clk`
- `input [1] rst`
- `input [1] s_ip_hdr_valid`
- `output [1] s_ip_hdr_ready`
- `input [47:0] s_eth_dest_mac`
- `input [47:0] s_eth_src_mac`
- `input [15:0] s_eth_type`
- `input [5:0] s_ip_dscp`
- `input [1:0] s_ip_ecn`
- `input [15:0] s_ip_length`
- `input [15:0] s_ip_identification`
- `input [2:0] s_ip_flags`
- `input [12:0] s_ip_fragment_offset`
- `input [7:0] s_ip_ttl`
- `input [7:0] s_ip_protocol`
- `input [31:0] s_ip_source_ip`
- `input [31:0] s_ip_dest_ip`
- `input [63:0] s_ip_payload_axis_tdata`
- `input [7:0] s_ip_payload_axis_tkeep`
- `input [1] s_ip_payload_axis_tvalid`
- `output [1] s_ip_payload_axis_tready`
- `input [1] s_ip_payload_axis_tlast`
- `input [1] s_ip_payload_axis_tuser`
- `output [1] m_eth_hdr_valid`
- `input [1] m_eth_hdr_ready`
- `output [47:0] m_eth_dest_mac`
- `output [47:0] m_eth_src_mac`
- `output [15:0] m_eth_type`
- `output [63:0] m_eth_payload_axis_tdata`
- `output [7:0] m_eth_payload_axis_tkeep`
- `output [1] m_eth_payload_axis_tvalid`
- `input [1] m_eth_payload_axis_tready`
- `output [1] m_eth_payload_axis_tlast`
- `output [1] m_eth_payload_axis_tuser`
- `output [1] busy`
- `output [1] error_payload_early_termination`

## Logic Block Types
- seq
