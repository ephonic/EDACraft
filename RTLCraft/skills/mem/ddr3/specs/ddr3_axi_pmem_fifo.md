# ddr3_axi_pmem_fifo

## Parameters
- `WIDTH = 8`
- `DEPTH = 4`
- `ADDR_W = 2`

## Ports (8)
- `input [1] clk_i`
- `input [1] rst_i`
- `input [WIDTH-1:0] data_in_i`
- `input [1] push_i`
- `input [1] pop_i`
- `output [WIDTH-1:0] data_out_o`
- `output [1] accept_o`
- `output [1] valid_o`

## FSM States
- `AXI4_BURST_FIXED` = 0
- `AXI4_BURST_INCR` = 1
- `AXI4_BURST_WRAP` = 2

## Logic Block Types
- seq
