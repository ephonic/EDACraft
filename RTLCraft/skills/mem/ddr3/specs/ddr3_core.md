# ddr3_core

## Parameters
- `DDR_MHZ = 25`
- `DDR_WRITE_LATENCY = 6`
- `DDR_READ_LATENCY = 5`
- `DDR_COL_W = 10`
- `DDR_BANK_W = 3`
- `DDR_ROW_W = 15`
- `DDR_BRC_MODE = 0`
- `WIDTH = 8`
- `DEPTH = 4`
- `ADDR_W = 2`

## Ports (32)
- `input [1] clk_i`
- `input [1] rst_i`
- `input [1] cfg_enable_i`
- `input [1] cfg_stb_i`
- `input [ 31:0] cfg_data_i`
- `input [ 15:0] inport_wr_i`
- `input [1] inport_rd_i`
- `input [ 31:0] inport_addr_i`
- `input [127:0] inport_write_data_i`
- `input [ 15:0] inport_req_id_i`
- `input [ 31:0] dfi_rddata_i`
- `input [1] dfi_rddata_valid_i`
- `input [  1:0] dfi_rddata_dnv_i`
- `output [1] cfg_stall_o`
- `output [1] inport_accept_o`
- `output [1] inport_ack_o`
- `output [1] inport_error_o`
- `output [ 15:0] inport_resp_id_o`
- `output [127:0] inport_read_data_o`
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
- `DDR_BANKS` = 0
- `DDR_BURST_LEN` = 1
- `CMD_W` = 2
- `CMD_NOP` = 3
- `CMD_ACTIVE` = 4
- `CMD_READ` = 5
- `CMD_WRITE` = 6
- `CMD_PRECHARGE` = 7
- `CMD_REFRESH` = 8
- `CMD_LOAD_MODE` = 9
- `CMD_ZQCL` = 10
- `MR0_REG` = 11
- `MR1_REG` = 12
- `MR2_REG` = 13
- `MR3_REG` = 14
- `STATE_W` = 15
- `STATE_INIT` = 16
- `STATE_DELAY` = 17
- `STATE_IDLE` = 18
- `STATE_ACTIVATE` = 19
- `STATE_READ` = 20
- `STATE_WRITE` = 21
- `STATE_PRECHARGE` = 22
- `STATE_REFRESH` = 23
- `AUTO_PRECHARGE` = 24
- `ALL_BANKS` = 25

## Logic Block Types
- seq
