# ct_mmu_tlboper

## Parameters
- `VPN_WIDTH = 39-12`
- `PPN_WIDTH = 40-12`
- `ASID_WIDTH = 16`
- `FLG_WIDTH = 14`
- `PGS_WIDTH = 3`
- `TAG_WIDTH = 1+VPN_WIDTH+ASID_WIDTH+PGS_WIDTH+1`
- `DATA_WIDTH = PPN_WIDTH+FLG_WIDTH`
- `PIDLE = 2'b00`
- `RIDLE = 2'b00`
- `WIIDLE = 2'b00`
- `WRIDLE = 2'b00`
- `IASID_IDLE = 3'b000`
- `IALL_IDLE = 1'b0`
- `IVA_IDLE = 4'b0000`

## Logic Block Types
- seq_async_reset
