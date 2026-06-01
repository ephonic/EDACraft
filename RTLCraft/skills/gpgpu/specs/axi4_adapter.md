# axi4_adapter

## Ports (10)
- `input [1] clk_i`
- `input [1] rst_ni`
- `output [1] busy_o`
- `input [1] req_i`
- `input [1] type_i`
- `input [3:0] amo_i`
- `output [1] gnt_o`
- `input [AXI_ADDR_WIDTH-1:0] addr_i`
- `input [1] we_i`
- `input [1] logic`

## FSM States
- `SINGLE_REQ` = 0
- `CACHE_LINE_REQ` = 1
- `BURST_FIXED` = 2
- `BURST_INCR` = 3
- `BURST_WRAP` = 4
- `RESP_OKAY` = 5
- `RESP_EXOKAY` = 6
- `RESP_SLVERR` = 7
- `RESP_DECERR` = 8
- `CACHE_BUFFERABLE` = 9
- `CACHE_MODIFIABLE` = 10
- `CACHE_RD_ALLOC` = 11
- `CACHE_WR_ALLOC` = 12
- `ATOP_ATOMICSWAP` = 13
- `ATOP_ATOMICCMP` = 14
- `ATOP_NONE` = 15
- `ATOP_ATOMICSTORE` = 16
- `ATOP_ATOMICLOAD` = 17
- `ATOP_LITTLE_END` = 18
- `ATOP_BIG_END` = 19
- `ATOP_ADD` = 20
- `ATOP_CLR` = 21
- `ATOP_EOR` = 22
- `ATOP_SET` = 23
- `ATOP_SMAX` = 24
- `ATOP_SMIN` = 25
- `ATOP_UMAX` = 26
- `ATOP_UMIN` = 27

## Logic Block Types
- always_comb
- always_ff
