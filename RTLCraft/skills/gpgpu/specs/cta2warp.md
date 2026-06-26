# cta2warp

## Ports (15)
- `input [1] clk`
- `input [1] rst_n`
- `output [1] cta_req_ready_o`
- `input [1] cta_req_valid_i`
- `input [`TAG_WIDTH-1:0] cta_req_dispatch2cu_wf_tag_dispatch_i`
- `input [1] cta_rsp_ready_i`
- `output [1] cta_rsp_valid_o`
- `output [`TAG_WIDTH-1:0] cta_rsp_cu2dispatch_wf_tag_done_o`
- `output [1] warpReq_valid_o`
- `output [`DEPTH_WARP-1:0] warpReq_wid_o`
- `output [1] warpRsp_ready_o`
- `input [1] warpRsp_valid_i`
- `input [`DEPTH_WARP-1:0] warpRsp_wid_i`
- `input [`DEPTH_WARP-1:0] wg_id_lookup_i`
- `output [`TAG_WIDTH-1:0] wg_id_tag_o`

## Logic Block Types
- seq_async_reset
