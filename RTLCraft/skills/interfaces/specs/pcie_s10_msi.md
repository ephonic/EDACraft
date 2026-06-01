# pcie_s10_msi

## Parameters
- `MSI_COUNT = 32`

## Ports (11)
- `input [1] clk`
- `input [1] rst`
- `input [MSI_COUNT-1:0] msi_irq`
- `output [1] app_msi_req`
- `input [1] app_msi_ack`
- `output [2:0] app_msi_tc`
- `output [4:0] app_msi_num`
- `output [1:0] app_msi_func_num`
- `input [1] cfg_msi_enable`
- `input [2:0] cfg_multiple_msi_enable`
- `input [31:0] cfg_msi_mask`

## Logic Block Types
- seq
