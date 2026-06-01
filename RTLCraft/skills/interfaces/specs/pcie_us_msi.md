# pcie_us_msi

## Parameters
- `MSI_COUNT = 32`

## Ports (20)
- `input [1] clk`
- `input [1] rst`
- `input [MSI_COUNT-1:0] msi_irq`
- `input [3:0] cfg_interrupt_msi_enable`
- `input [7:0] cfg_interrupt_msi_vf_enable`
- `input [11:0] cfg_interrupt_msi_mmenable`
- `input [1] cfg_interrupt_msi_mask_update`
- `input [31:0] cfg_interrupt_msi_data`
- `output [3:0] cfg_interrupt_msi_select`
- `output [31:0] cfg_interrupt_msi_int`
- `output [31:0] cfg_interrupt_msi_pending_status`
- `output [1] cfg_interrupt_msi_pending_status_data_enable`
- `output [3:0] cfg_interrupt_msi_pending_status_function_num`
- `input [1] cfg_interrupt_msi_sent`
- `input [1] cfg_interrupt_msi_fail`
- `output [2:0] cfg_interrupt_msi_attr`
- `output [1] cfg_interrupt_msi_tph_present`
- `output [1:0] cfg_interrupt_msi_tph_type`
- `output [8:0] cfg_interrupt_msi_tph_st_tag`
- `output [3:0] cfg_interrupt_msi_function_number`

## Logic Block Types
- seq
