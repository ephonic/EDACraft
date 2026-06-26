# wf_done_interface_single

## Ports (7)
- `input [1] clk`
- `input [1] rst_n`
- `input [1] wf_done_i`
- `input [`WG_ID_WIDTH-1:0] wf_done_wg_id_i`
- `input [1] host_wf_done_ready_i`
- `output [1] host_wf_done_valid_o`
- `output [`WG_ID_WIDTH-1:0] host_wf_done_wg_id_o`
