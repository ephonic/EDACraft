# csrexe

## Ports (36)
- `input [1] clk`
- `input [1] rst_n`
- `input [31:0] ctrl_inst_i`
- `input [1:0] ctrl_csr_i`
- `input [1] ctrl_custom_signal_0_i`
- `input [1] ctrl_isvec_i`
- `input [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] ctrl_reg_idxw_i`
- `input [1] ctrl_wxd_i`
- `input [`DEPTH_WARP-1:0] ctrl_wid_i`
- `input [1] in_valid_i`
- `input [1] out_ready_i`
- `input [`XLEN-1:0] in1_i`
- `input [`DEPTH_WARP*3-1:0] rm_wid_i`
- `input [`DEPTH_WARP-1:0] lsu_wid_i`
- `input [`DEPTH_WARP-1:0] simt_wid_i`
- `input [1] CTA2csr_valid_i`
- `input [`WF_COUNT_WIDTH-1:0] dispatch2cu_wg_wf_count_i`
- `input [`WAVE_ITEM_WIDTH-1:0] dispatch2cu_wf_size_dispatch_i`
- `input [`SGPR_ID_WIDTH:0] dispatch2cu_sgpr_base_dispatch_i`
- `input [`VGPR_ID_WIDTH:0] dispatch2cu_vgpr_base_dispatch_i`
- `input [`TAG_WIDTH-1:0] dispatch2cu_wf_tag_dispatch_i`
- `input [`LDS_ID_WIDTH:0] dispatch2cu_lds_base_dispatch_i`
- `input [`MEM_ADDR_WIDTH-1:0] dispatch2cu_pds_base_dispatch_i`
- `input [`MEM_ADDR_WIDTH-1:0] dispatch2cu_csr_knl_dispatch_i`
- `input [`WG_SIZE_X_WIDTH-1:0] dispatch2cu_wgid_x_dispatch_i`
- `input [`WG_SIZE_Y_WIDTH-1:0] dispatch2cu_wgid_y_dispatch_i`
- `input [`WG_SIZE_Z_WIDTH-1:0] dispatch2cu_wgid_z_dispatch_i`
- `input [31:0] dispatch2cu_wg_id_i`
- `input [`DEPTH_WARP-1:0] wid_i`
- `output [1] in_ready_o`
- `output [1] out_valid_o`
- `output [`XLEN-1:0] wb_wxd_rd_o`
- `output [1] wxd_o`
- `output [`REGIDX_WIDTH+`REGEXT_WIDTH-1:0] reg_idxw_o`
- `output [`DEPTH_WARP-1:0] warp_id_o`
- `output [8:0] rm_o`

## Submodule Instances
- `U_vcsr_i`
