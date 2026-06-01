# ddr3_dfi_seq

## Parameters
- `DDR_MHZ = 50`
- `DDR_WRITE_LATENCY = 6`
- `DDR_READ_LATENCY = 5`
- `DDR_BURST_LEN = 4`
- `DDR_COL_W = 9`
- `DDR_BANK_W = 3`
- `DDR_ROW_W = 15`
- `DDR_DATA_W = 32`
- `DDR_DQM_W = 4`
- `WIDTH = 144`
- `DEPTH = 2`
- `ADDR_W = 1`

## Ports (27)
- `input [1] clk_i`
- `input [1] rst_i`
- `input [ 14:0] address_i`
- `input [  2:0] bank_i`
- `input [  3:0] command_i`
- `input [1] cke_i`
- `input [127:0] wrdata_i`
- `input [ 15:0] wrdata_mask_i`
- `input [ 31:0] dfi_rddata_i`
- `input [1] dfi_rddata_valid_i`
- `input [  1:0] dfi_rddata_dnv_i`
- `output [1] accept_o`
- `output [127:0] rddata_o`
- `output [1] rddata_valid_o`
- `output [ 14:0] dfi_address_o`
- `output [  2:0] dfi_bank_o`
- `output [1] dfi_cas_n_o`
- `output [1] dfi_cke_o`
- `output [1] dfi_cs_n_o`
- `output [1] dfi_odt_o`
- `output [1] dfi_ras_n_o`
- `output [1] dfi_reset_n_o`
- `output [1] dfi_we_n_o`
- `output [ 31:0] dfi_wrdata_o`
- `output [1] dfi_wrdata_en_o`
- `output [  3:0] dfi_wrdata_mask_o`
- `output [1] dfi_rddata_en_o`

## FSM States
- `DDR_TWTR_CYCLES` = 0
- `CMD_W` = 1
- `CMD_NOP` = 2
- `CMD_ACTIVE` = 3
- `CMD_READ` = 4
- `CMD_WRITE` = 5
- `CMD_ZQCL` = 6
- `CMD_PRECHARGE` = 7
- `CMD_REFRESH` = 8
- `CMD_LOAD_MODE` = 9
- `DELAY_W` = 10
- `CMD_ACCEPT_W` = 11

## Logic Block Types
- seq
