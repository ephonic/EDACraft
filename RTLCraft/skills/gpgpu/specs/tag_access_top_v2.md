# tag_access_top_v2

## Parameters
- `NUM_SET = `DCACHE_NSETS`
- `NUM_WAY = `DCACHE_NWAYS`
- `TAG_BITS = `DCACHE_TAGBITS`

## Ports (4)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] probeRead_valid_i`
- `output [1] probeRead_ready_o`

## Submodule Instances
- `U_probe_read_buffer`
- `U_tag_body_access`
- `U_fixed_pri_tagAccessRArb`
- `U_one2bin_tagAccessRArb`
- `U_lru_matrix`
- `U_bin2one_lru_index_out`
- `U_tag_checker`
- `U_cacheHit_hold`
- `U_one2bin_tagchecker_waymask`
- `U_fixed_pri_choosenDirty_set_valid`
- `U_one2bin_chooseDirty_set_valid`

## Logic Block Types
- comb
- seq_async_reset
