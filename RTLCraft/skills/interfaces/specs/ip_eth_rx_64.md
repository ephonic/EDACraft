# ip_eth_rx_64

## Ports (42)
- `input [1] clk`
- `input [1] rst`
- `input [1] s_eth_hdr_valid`
- `output [1] s_eth_hdr_ready`
- `input [47:0] s_eth_dest_mac`
- `input [47:0] s_eth_src_mac`
- `input [15:0] s_eth_type`
- `input [63:0] s_eth_payload_axis_tdata`
- `input [7:0] s_eth_payload_axis_tkeep`
- `input [1] s_eth_payload_axis_tvalid`
- `output [1] s_eth_payload_axis_tready`
- `input [1] s_eth_payload_axis_tlast`
- `input [1] s_eth_payload_axis_tuser`
- `output [1] m_ip_hdr_valid`
- `input [1] m_ip_hdr_ready`
- `output [47:0] m_eth_dest_mac`
- `output [47:0] m_eth_src_mac`
- `output [15:0] m_eth_type`
- `output [3:0] m_ip_version`
- `output [3:0] m_ip_ihl`
- `output [5:0] m_ip_dscp`
- `output [1:0] m_ip_ecn`
- `output [15:0] m_ip_length`
- `output [15:0] m_ip_identification`
- `output [2:0] m_ip_flags`
- `output [12:0] m_ip_fragment_offset`
- `output [7:0] m_ip_ttl`
- `output [7:0] m_ip_protocol`
- `output [15:0] m_ip_header_checksum`
- `output [31:0] m_ip_source_ip`
- `output [31:0] m_ip_dest_ip`
- `output [63:0] m_ip_payload_axis_tdata`
- `output [7:0] m_ip_payload_axis_tkeep`
- `output [1] m_ip_payload_axis_tvalid`
- `input [1] m_ip_payload_axis_tready`
- `output [1] m_ip_payload_axis_tlast`
- `output [1] m_ip_payload_axis_tuser`
- `output [1] busy`
- `output [1] error_header_early_termination`
- `output [1] error_payload_early_termination`
- `output [1] error_invalid_header`
- `output [1] error_invalid_checksum`

## Logic Block Types
- seq
