# ct_mmu_jtlb

## Parameters
- `VPN_WIDTH = 39-12`
- `PPN_WIDTH = 40-12`
- `FLG_WIDTH = 14`
- `PGS_WIDTH = 3`
- `ASID_WIDTH = 16`
- `PTE_LEVEL = 3`
- `VPN_PERLEL = VPN_WIDTH/PTE_LEVEL`
- `TAG_WIDTH = 1+VPN_WIDTH+ASID_WIDTH+PGS_WIDTH+1`
- `DATA_WIDTH = PPN_WIDTH+FLG_WIDTH`
- `READ_IDLE = 3'b000`
- `PFU_IDLE = 2'b00`

## Logic Block Types
- seq_async_reset
