# pcie_s10_cfg

## Parameters
- `L_TILE = 0`
- `PF_COUNT = 1`

## Ports (55)
- `input [1] clk`
- `input [1] rst`
- `input [31:0] tl_cfg_ctl`
- `input [4:0] tl_cfg_add`
- `input [1:0] tl_cfg_func`
- `output [PF_COUNT-1:0] cfg_memory_space_en`
- `output [PF_COUNT-1:0] cfg_ido_cpl_en`
- `output [PF_COUNT-1:0] cfg_perr_en`
- `output [PF_COUNT-1:0] cfg_serr_en`
- `output [PF_COUNT-1:0] cfg_fatal_err_rpt_en`
- `output [PF_COUNT-1:0] cfg_nonfatal_err_rpt_en`
- `output [PF_COUNT-1:0] cfg_corr_err_rpt_en`
- `output [PF_COUNT-1:0] cfg_unsupported_req_rpt_en`
- `output [PF_COUNT-1:0] cfg_bus_master_en`
- `output [PF_COUNT-1:0] cfg_ext_tag_en`
- `output [PF_COUNT*3-1:0] cfg_max_read_request_size`
- `output [PF_COUNT*3-1:0] cfg_max_payload_size`
- `output [PF_COUNT-1:0] cfg_ido_request_en`
- `output [PF_COUNT-1:0] cfg_no_snoop_en`
- `output [PF_COUNT-1:0] cfg_relaxed_ordering_en`
- `output [PF_COUNT*5-1:0] cfg_device_num`
- `output [PF_COUNT*8-1:0] cfg_bus_num`
- `output [PF_COUNT-1:0] cfg_pm_no_soft_rst`
- `output [PF_COUNT-1:0] cfg_rcb_ctrl`
- `output [PF_COUNT-1:0] cfg_irq_disable`
- `output [PF_COUNT*5-1:0] cfg_pcie_cap_irq_msg_num`
- `output [PF_COUNT-1:0] cfg_sys_pwr_ctrl`
- `output [PF_COUNT*2-1:0] cfg_sys_atten_ind_ctrl`
- `output [PF_COUNT*2-1:0] cfg_sys_pwr_ind_ctrl`
- `output [PF_COUNT*16-1:0] cfg_num_vf`
- `output [PF_COUNT*5-1:0] cfg_ats_stu`
- `output [PF_COUNT-1:0] cfg_ats_cache_en`
- `output [PF_COUNT-1:0] cfg_ari_forward_en`
- `output [PF_COUNT-1:0] cfg_atomic_request_en`
- `output [PF_COUNT*3-1:0] cfg_tph_st_mode`
- `output [PF_COUNT*2-1:0] cfg_tph_en`
- `output [PF_COUNT-1:0] cfg_vf_en`
- `output [PF_COUNT*4-1:0] cfg_an_link_speed`
- `output [PF_COUNT*6-1:0] cfg_an_link_width`
- `output [PF_COUNT*11-1:0] cfg_start_vf_index`
- `output [PF_COUNT*64-1:0] cfg_msi_address`
- `output [PF_COUNT*32-1:0] cfg_msi_mask`
- `output [PF_COUNT-1:0] cfg_send_f_err`
- `output [PF_COUNT-1:0] cfg_send_nf_err`
- `output [PF_COUNT-1:0] cfg_send_cor_err`
- `output [PF_COUNT*5-1:0] cfg_aer_irq_msg_num`
- `output [PF_COUNT-1:0] cfg_msix_func_mask`
- `output [PF_COUNT-1:0] cfg_msix_enable`
- `output [PF_COUNT*3-1:0] cfg_multiple_msi_enable`
- `output [PF_COUNT-1:0] cfg_64bit_msi`
- `output [PF_COUNT-1:0] cfg_msi_enable`
- `output [PF_COUNT*16-1:0] cfg_msi_data`
- `output [PF_COUNT*32-1:0] cfg_aer_uncor_err_mask`
- `output [PF_COUNT*32-1:0] cfg_aer_corr_err_mask`
- `output [PF_COUNT*32-1:0] cfg_aer_uncor_err_severity`

## Logic Block Types
- seq
