# ddr3_dfi_phy

## Parameters
- `REFCLK_FREQUENCY = 200`
- `DQS_TAP_DELAY_INIT = 15`
- `DQ_TAP_DELAY_INIT = 1`
- `TPHY_RDLAT = 4`
- `TPHY_WRLAT = 3`
- `TPHY_WRDATA = 0`

## Ports (38)
- `input [1] clk_i`
- `input [1] clk_ddr_i`
- `input [1] clk_ddr90_i`
- `input [1] clk_ref_i`
- `input [1] rst_i`
- `input [1] cfg_valid_i`
- `input [ 31:0] cfg_i`
- `input [ 14:0] dfi_address_i`
- `input [  2:0] dfi_bank_i`
- `input [1] dfi_cas_n_i`
- `input [1] dfi_cke_i`
- `input [1] dfi_cs_n_i`
- `input [1] dfi_odt_i`
- `input [1] dfi_ras_n_i`
- `input [1] dfi_reset_n_i`
- `input [1] dfi_we_n_i`
- `input [ 31:0] dfi_wrdata_i`
- `input [1] dfi_wrdata_en_i`
- `input [  3:0] dfi_wrdata_mask_i`
- `input [1] dfi_rddata_en_i`
- `output [ 31:0] dfi_rddata_o`
- `output [1] dfi_rddata_valid_o`
- `output [  1:0] dfi_rddata_dnv_o`
- `output [1] ddr3_ck_p_o`
- `output [1] ddr3_ck_n_o`
- `output [1] ddr3_cke_o`
- `output [1] ddr3_reset_n_o`
- `output [1] ddr3_ras_n_o`
- `output [1] ddr3_cas_n_o`
- `output [1] ddr3_we_n_o`
- `output [1] ddr3_cs_n_o`
- `output [  2:0] ddr3_ba_o`
- `output [ 13:0] ddr3_addr_o`
- `output [1] ddr3_odt_o`
- `output [  1:0] ddr3_dm_o`
- `inout [  1:0] ddr3_dqs_p_io`
- `inout [  1:0] ddr3_dqs_n_io`
- `inout [ 15:0] ddr3_dq_io`

## FSM States
- `RD_SHIFT_W` = 0

## Submodule Instances
- `OBUFDS`
- `IOBUFDS`
- `OSERDESE2`
- `IOBUF`
- `IDELAYE2`
- `IDELAYCTRL`
- `ISERDESE2`

## Logic Block Types
- seq
