# ct_mmu_arb

## Parameters
- `VPN_WIDTH = 39-12`
- `PPN_WIDTH = 40-12`
- `FLG_WIDTH = 14`
- `PGS_WIDTH = 3`
- `ASID_WIDTH = 16`
- `TAG_WIDTH = 1+VPN_WIDTH+ASID_WIDTH+PGS_WIDTH+1`
- `DATA_WIDTH = PPN_WIDTH+FLG_WIDTH`
- `ARB_IDLE = 2'b00`

## Logic Block Types
- seq_async_reset
