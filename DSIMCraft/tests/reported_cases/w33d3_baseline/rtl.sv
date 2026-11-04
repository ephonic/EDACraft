// Generated from owned AST/IR; functional qualification is separate.
module agent_event_module (
  input wire [0:0] clk_c0,
  input wire [0:0] clk_c1,
  input wire [0:0] clk_c2,
  input wire [0:0] rst_r0,
  input wire [32:0] in_x,
  input wire [0:0] in_en,
  output wire [32:0] out_state0,
  output wire [32:0] out_state1,
  output wire [32:0] out_state2,
  output wire [32:0] out_shifted
);
  reg [32:0] r_q0;
  reg [32:0] r_q1;
  reg [32:0] r_q2;
  wire [32:0] n_zero;
  assign n_zero = 33'd0;
  wire [32:0] n_sum;
  assign n_sum = (r_q0 + in_x);
  wire [32:0] n_discard;
  assign n_discard = (in_x ^ in_x);
  wire [32:0] n_mix1;
  assign n_mix1 = (r_q0 ^ in_x);
  wire [32:0] n_mix2;
  assign n_mix2 = (r_q1 ^ in_x);
  wire [32:0] n_shift;
  assign n_shift = {1'd0, r_q0[32:1]};
  wire [32:0] n_identity;
  assign n_identity = (n_sum + n_zero);
  assign out_state0 = r_q0;
  assign out_state1 = r_q1;
  assign out_state2 = r_q2;
  assign out_shifted = n_shift;
  always @(posedge clk_c0 or negedge rst_r0)
    if ((!rst_r0))
      r_q0 <= 33'd0;
    else
      if (in_en)
        r_q0 <= n_identity;
  always @(negedge clk_c1)
    if ((!rst_r0))
      r_q1 <= 33'd1;
    else
      r_q1 <= n_mix1;
  always @(posedge clk_c2 or negedge rst_r0)
    if ((!rst_r0))
      r_q2 <= 33'd2;
    else
      r_q2 <= n_mix2;
endmodule

