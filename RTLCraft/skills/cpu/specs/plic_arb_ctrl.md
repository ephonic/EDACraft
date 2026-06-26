# plic_arb_ctrl

## Parameters
- `INT_NUM = 1024`
- `ECH_RD = 32`
- `PRIO_BIT = 5`
- `RD_NUM = INT_NUM/ECH_RD`
- `CLOG_BIT = clog2(RD_NUM-1)`
- `RD_BIT = (CLOG_BIT==0) ? 1 : CLOG_BIT`
- `IDLE = 2'b00`
- `ARBTRATE = 2'b01`
- `ARB_DELAY = 2'b10`
- `WRITE_CLAIM = 2'b11`
- `ADD_NUM = 1024-INT_NUM`
- `ADD_RD_WITH = 5 - RD_BIT`

## Logic Block Types
- seq_async_reset
