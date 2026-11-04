// Generated from owned AST/IR; functional qualification is separate.
module agent_generic_module (
  input wire [0:0] clk,
  input wire [0:0] rst_n,
  input wire [0:0] in_enable,
  input wire [12:0] in_u13_0,
  input wire [12:0] in_u13_1,
  input wire [12:0] in_u13_2,
  input wire signed [32:0] in_s33_0,
  input wire signed [32:0] in_s33_1,
  input wire signed [32:0] in_s33_2,
  input wire signed [32:0] in_s33_3,
  input wire signed [32:0] in_s33_4,
  input wire [63:0] in_u64_0,
  input wire [63:0] in_u64_1,
  input wire [63:0] in_u64_2,
  input wire [63:0] in_u64_3,
  input wire [63:0] in_u64_4,
  input wire [63:0] in_u64_5,
  input wire [63:0] in_u64_6,
  input wire [63:0] in_u64_7,
  input wire signed [63:0] in_s64_0,
  input wire signed [63:0] in_s64_1,
  input wire signed [63:0] in_s64_2,
  input wire signed [63:0] in_s64_3,
  output wire [12:0] out_u13_value,
  output wire [12:0] out_u13_held,
  output wire signed [32:0] out_s33_value,
  output wire signed [32:0] out_s33_held,
  output wire [63:0] out_u64_value,
  output wire [63:0] out_u64_held,
  output wire signed [63:0] out_s64_value,
  output wire signed [63:0] out_s64_held
);
  reg [12:0] r_u13_saved;
  reg signed [32:0] r_s33_saved;
  reg [63:0] r_u64_saved;
  reg signed [63:0] r_s64_saved;
  wire [12:0] n_u13_partial1;
  assign n_u13_partial1 = ($unsigned(in_u13_0) + $unsigned(in_u13_1));
  wire signed [32:0] n_s33_partial1;
  assign n_s33_partial1 = ($unsigned(in_s33_0) + $unsigned(in_s33_1));
  wire [63:0] n_u64_partial1;
  assign n_u64_partial1 = ($unsigned(in_u64_0) + $unsigned(in_u64_1));
  wire signed [63:0] n_s64_partial1;
  assign n_s64_partial1 = ($unsigned(in_s64_0) + $unsigned(in_s64_1));
  wire [12:0] n_u13_sum;
  assign n_u13_sum = ($unsigned(n_u13_partial1) + $unsigned(in_u13_2));
  wire signed [32:0] n_s33_partial2;
  assign n_s33_partial2 = ($unsigned(n_s33_partial1) + $unsigned(in_s33_2));
  wire [63:0] n_u64_partial2;
  assign n_u64_partial2 = ($unsigned(n_u64_partial1) + $unsigned(in_u64_2));
  wire signed [63:0] n_s64_partial2;
  assign n_s64_partial2 = ($unsigned(n_s64_partial1) + $unsigned(in_s64_2));
  wire signed [32:0] n_s33_partial3;
  assign n_s33_partial3 = ($unsigned(n_s33_partial2) + $unsigned(in_s33_3));
  wire [63:0] n_u64_partial3;
  assign n_u64_partial3 = ($unsigned(n_u64_partial2) + $unsigned(in_u64_3));
  wire signed [63:0] n_s64_sum;
  assign n_s64_sum = ($unsigned(n_s64_partial2) + $unsigned(in_s64_3));
  wire signed [32:0] n_s33_sum;
  assign n_s33_sum = ($unsigned(n_s33_partial3) + $unsigned(in_s33_4));
  wire [63:0] n_u64_partial4;
  assign n_u64_partial4 = ($unsigned(n_u64_partial3) + $unsigned(in_u64_4));
  wire [63:0] n_u64_partial5;
  assign n_u64_partial5 = ($unsigned(n_u64_partial4) + $unsigned(in_u64_5));
  wire [63:0] n_u64_partial6;
  assign n_u64_partial6 = ($unsigned(n_u64_partial5) + $unsigned(in_u64_6));
  wire [63:0] n_u64_sum;
  assign n_u64_sum = ($unsigned(n_u64_partial6) + $unsigned(in_u64_7));
  assign out_u13_value = n_u13_sum;
  assign out_u13_held = r_u13_saved;
  assign out_s33_value = n_s33_sum;
  assign out_s33_held = r_s33_saved;
  assign out_u64_value = n_u64_sum;
  assign out_u64_held = r_u64_saved;
  assign out_s64_value = n_s64_sum;
  assign out_s64_held = r_s64_saved;
  always @(posedge clk or negedge rst_n)
    begin
      if ((!rst_n))
        begin
          r_u13_saved <= 13'd0;
          r_s33_saved <= 33'd0;
          r_u64_saved <= 64'd0;
          r_s64_saved <= 64'd0;
        end
      else
        begin
          if (in_enable)
            r_u13_saved <= n_u13_sum;
          if (in_enable)
            r_s33_saved <= n_s33_sum;
          if (in_enable)
            r_u64_saved <= n_u64_sum;
          if (in_enable)
            r_s64_saved <= n_s64_sum;
        end
    end
endmodule

