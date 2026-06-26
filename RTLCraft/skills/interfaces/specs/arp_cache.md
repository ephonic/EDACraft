# arp_cache

## Parameters
- `CACHE_ADDR_WIDTH = 9`

## Ports (14)
- `input [1] clk`
- `input [1] rst`
- `input [1] query_request_valid`
- `output [1] query_request_ready`
- `input [31:0] query_request_ip`
- `output [1] query_response_valid`
- `input [1] query_response_ready`
- `output [1] query_response_error`
- `output [47:0] query_response_mac`
- `input [1] write_request_valid`
- `output [1] write_request_ready`
- `input [31:0] write_request_ip`
- `input [47:0] write_request_mac`
- `input [1] clear_cache`

## Logic Block Types
- seq
