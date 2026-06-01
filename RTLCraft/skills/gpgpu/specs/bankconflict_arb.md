# bankconflict_arb

## Ports (14)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] core_req_arb_is_write_i`
- `input [1] core_req_arb_enable_i`
- `input [`SHAREMEM_NLANES-1:0] core_req_arb_activemask_i`
- `input [`SHAREMEM_NLANES*`DCACHE_BLOCKOFFSETBITS-1:0] core_req_arb_blockoffset_i`
- `input [`SHAREMEM_NLANES*`BYTESOFWORD-1:0] core_req_arb_wordoffset1h_i`
- `output [`SHAREMEM_NBANKS*`SHAREMEM_NLANES-1:0] data_crsbar_write_sel1h_o`
- `output [`SHAREMEM_NLANES*`SHAREMEM_NBANKS-1:0] data_crsbar_read_sel1h_o`
- `output [`SHAREMEM_NBANKS*`SHAREMEM_BANKOFFSET-1:0] data_crsbar_out_bankoffset_o`
- `output [`SHAREMEM_NBANKS*`BYTESOFWORD-1:0] data_crsbar_out_wordoffset1h_o`
- `output [`SHAREMEM_NBANKS-1:0] data_array_en_o`
- `output [`SHAREMEM_NLANES-1:0] active_lane_o`
- `output [1] bankconflict_o`

## Logic Block Types
- seq_async_reset
