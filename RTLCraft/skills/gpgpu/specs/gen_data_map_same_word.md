# gen_data_map_same_word

## Ports (8)
- `input [1*`DCACHE_NLANES-1:0] perLaneAddr_activeMask_i`
- `input [`DCACHE_BLOCKOFFSETBITS*`DCACHE_NLANES-1:0] perLaneAddr_blockOffset_i`
- `input [`BYTESOFWORD*`DCACHE_NLANES-1:0] perLaneAddr_wordOffset1H_i`
- `input [`WORDLENGTH*`DCACHE_NLANES-1:0] data_i`
- `output [1*`DCACHE_NLANES-1:0] perLaneAddrRemap_activeMask_o`
- `output [`DCACHE_BLOCKOFFSETBITS*`DCACHE_NLANES-1:0] perLaneAddrRemap_blockOffset_o`
- `output [`BYTESOFWORD*`DCACHE_NLANES-1:0] perLaneAddrRemap_wordOffset1H_o`
- `output [`WORDLENGTH*`DCACHE_NLANES-1:0] data_o`

## Logic Block Types
- comb
