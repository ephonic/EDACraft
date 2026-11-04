// Generated from owned AST/IR; functional qualification is separate.
module producer (
  input wire clk,
  input wire rst_n,
  input wire valid,
  input wire ready,
  input wire [12:0] data,
  input wire [6:0] tag,
  input wire last,
  output wire valid_o,
  output wire ready_o,
  output wire [12:0] data_o,
  output wire [6:0] tag_o,
  output wire last_o
);
  assign valid_o = (valid && rst_n);
  assign ready_o = (ready && rst_n);
  assign data_o = (data ^ 13'd2730);
  assign tag_o = tag;
  assign last_o = last;
endmodule

module consumer (
  input wire clk,
  input wire rst_n,
  input wire valid,
  input wire ready,
  input wire [12:0] data,
  input wire [6:0] tag,
  input wire last,
  output wire valid_o,
  output wire ready_o,
  output wire [12:0] data_o,
  output wire [6:0] tag_o,
  output wire last_o
);
  assign valid_o = (valid && rst_n);
  assign ready_o = (ready && rst_n);
  assign data_o = (data ^ 13'd1638);
  assign tag_o = tag;
  assign last_o = last;
endmodule

module dut (
  input wire clk,
  input wire rst_n,
  input wire in_valid,
  input wire out_ready,
  input wire [12:0] in_data,
  input wire [6:0] in_tag,
  input wire in_last,
  output wire out_valid,
  output wire in_ready,
  output wire [12:0] out_data,
  output wire [6:0] out_tag,
  output wire out_last
);
  wire [0:0] rtl_agent_main_0;
  wire [0:0] rtl_agent_main_1;
  wire [12:0] rtl_agent_main_2;
  wire [6:0] rtl_agent_main_3;
  wire [0:0] rtl_agent_main_4;
  wire v;
  wire r;
  wire l;
  wire [12:0] d;
  wire [6:0] t;
  producer p(.clk(clk), .rst_n(rst_n), .valid(in_valid), .ready(r), .data(in_data), .tag(in_tag), .last(in_last), .valid_o(v), .ready_o(in_ready), .data_o(d), .tag_o(t), .last_o(l));
  consumer c(.clk(clk), .rst_n(rst_n), .valid(rtl_agent_main_0), .ready(out_ready), .data(rtl_agent_main_2), .tag(rtl_agent_main_3), .last(rtl_agent_main_4), .valid_o(out_valid), .ready_o(rtl_agent_main_1), .data_o(out_data), .tag_o(out_tag), .last_o(out_last));
  rtl_agent_main_elastic rtl_agent_main_pipe(.clk(clk), .rst_n(rst_n), .i_valid(v), .o_valid(rtl_agent_main_0), .i_ready(r), .o_ready(rtl_agent_main_1), .i_0(d), .o_0(rtl_agent_main_2), .i_1(t), .o_1(rtl_agent_main_3), .i_2(l), .o_2(rtl_agent_main_4));
endmodule

module rtl_agent_main_elastic (
  input logic [0:0] clk,
  input logic [0:0] rst_n,
  input logic [0:0] i_valid,
  output logic [0:0] i_ready,
  output logic [0:0] o_valid,
  input logic [0:0] o_ready,
  input logic [12:0] i_0,
  output logic [12:0] o_0,
  input logic [6:0] i_1,
  output logic [6:0] o_1,
  input logic [0:0] i_2,
  output logic [0:0] o_2
);
  reg h0;
  reg t0;
  wire r0;
  wire push0;
  wire pop0;
  reg [12:0] d0_0;
  reg [12:0] q0_0;
  reg [6:0] d0_1;
  reg [6:0] q0_1;
  reg [0:0] d0_2;
  reg [0:0] q0_2;
  reg h1;
  reg t1;
  wire r1;
  wire push1;
  wire pop1;
  reg [12:0] d1_0;
  reg [12:0] q1_0;
  reg [6:0] d1_1;
  reg [6:0] q1_1;
  reg [0:0] d1_2;
  reg [0:0] q1_2;
  assign r0 = (rst_n && (!t0));
  assign push0 = (i_valid && r0);
  assign pop0 = (h0 && r1);
  assign r1 = (rst_n && (!t1));
  assign push1 = (h0 && r1);
  assign pop1 = (h1 && o_ready);
  assign i_ready = r0;
  assign o_valid = (rst_n && h1);
  assign o_0 = (o_valid ? d1_0 : 13'd0);
  assign o_1 = (o_valid ? d1_1 : 7'd0);
  assign o_2 = (o_valid ? d1_2 : 1'd0);
  always_ff @(posedge clk or negedge rst_n)
    if ((!rst_n))
      begin
        h0 <= 1'd0;
        t0 <= 1'd0;
        d0_0 <= 13'd0;
        q0_0 <= 13'd0;
        d0_1 <= 7'd0;
        q0_1 <= 7'd0;
        d0_2 <= 1'd0;
        q0_2 <= 1'd0;
        h1 <= 1'd0;
        t1 <= 1'd0;
        d1_0 <= 13'd0;
        q1_0 <= 13'd0;
        d1_1 <= 7'd0;
        q1_1 <= 7'd0;
        d1_2 <= 1'd0;
        q1_2 <= 1'd0;
      end
    else
      begin
        h0 <= (t0 || ((h0 && (!pop0)) || push0));
        t0 <= ((!pop0) && (t0 || (h0 && push0)));
        if ((pop0 && t0))
          d0_0 <= q0_0;
        else
          if ((push0 && ((!h0) || pop0)))
            d0_0 <= i_0;
        if ((push0 && (h0 && (!pop0))))
          q0_0 <= i_0;
        if ((pop0 && t0))
          d0_1 <= q0_1;
        else
          if ((push0 && ((!h0) || pop0)))
            d0_1 <= i_1;
        if ((push0 && (h0 && (!pop0))))
          q0_1 <= i_1;
        if ((pop0 && t0))
          d0_2 <= q0_2;
        else
          if ((push0 && ((!h0) || pop0)))
            d0_2 <= i_2;
        if ((push0 && (h0 && (!pop0))))
          q0_2 <= i_2;
        h1 <= (t1 || ((h1 && (!pop1)) || push1));
        t1 <= ((!pop1) && (t1 || (h1 && push1)));
        if ((pop1 && t1))
          d1_0 <= q1_0;
        else
          if ((push1 && ((!h1) || pop1)))
            d1_0 <= d0_0;
        if ((push1 && (h1 && (!pop1))))
          q1_0 <= d0_0;
        if ((pop1 && t1))
          d1_1 <= q1_1;
        else
          if ((push1 && ((!h1) || pop1)))
            d1_1 <= d0_1;
        if ((push1 && (h1 && (!pop1))))
          q1_1 <= d0_1;
        if ((pop1 && t1))
          d1_2 <= q1_2;
        else
          if ((push1 && ((!h1) || pop1)))
            d1_2 <= d0_2;
        if ((push1 && (h1 && (!pop1))))
          q1_2 <= d0_2;
      end
endmodule

