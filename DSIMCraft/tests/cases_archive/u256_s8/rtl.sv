// Generated from owned AST/IR; functional qualification is separate.
module producer (
  input wire clk,
  input wire rst_n,
  input wire valid,
  input wire ready,
  input wire [255:0] data,
  input wire [6:0] tag,
  input wire last,
  output wire valid_o,
  output wire ready_o,
  output wire [255:0] data_o,
  output wire [6:0] tag_o,
  output wire last_o
);
  assign valid_o = (valid && rst_n);
  assign ready_o = (ready && rst_n);
  assign data_o = (data ^ 256'd38597363079105398474523661669562635951089994888546854679819194669304376546645);
  assign tag_o = tag;
  assign last_o = last;
endmodule

module consumer (
  input wire clk,
  input wire rst_n,
  input wire valid,
  input wire ready,
  input wire [255:0] data,
  input wire [6:0] tag,
  input wire last,
  output wire valid_o,
  output wire ready_o,
  output wire [255:0] data_o,
  output wire [6:0] tag_o,
  output wire last_o
);
  assign valid_o = (valid && rst_n);
  assign ready_o = (ready && rst_n);
  assign data_o = (data ^ 256'd23158417847463239084714197001737581570653996933128112807891516801582625927987);
  assign tag_o = tag;
  assign last_o = last;
endmodule

module dut (
  input wire clk,
  input wire rst_n,
  input wire in_valid,
  input wire out_ready,
  input wire [255:0] in_data,
  input wire [6:0] in_tag,
  input wire in_last,
  output wire out_valid,
  output wire in_ready,
  output wire [255:0] out_data,
  output wire [6:0] out_tag,
  output wire out_last
);
  wire [0:0] rtl_agent_main_0;
  wire [0:0] rtl_agent_main_1;
  wire [255:0] rtl_agent_main_2;
  wire [6:0] rtl_agent_main_3;
  wire [0:0] rtl_agent_main_4;
  wire v;
  wire r;
  wire l;
  wire [255:0] d;
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
  input logic [255:0] i_0,
  output logic [255:0] o_0,
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
  reg [255:0] d0_0;
  reg [255:0] q0_0;
  reg [6:0] d0_1;
  reg [6:0] q0_1;
  reg [0:0] d0_2;
  reg [0:0] q0_2;
  reg h1;
  reg t1;
  wire r1;
  wire push1;
  wire pop1;
  reg [255:0] d1_0;
  reg [255:0] q1_0;
  reg [6:0] d1_1;
  reg [6:0] q1_1;
  reg [0:0] d1_2;
  reg [0:0] q1_2;
  reg h2;
  reg t2;
  wire r2;
  wire push2;
  wire pop2;
  reg [255:0] d2_0;
  reg [255:0] q2_0;
  reg [6:0] d2_1;
  reg [6:0] q2_1;
  reg [0:0] d2_2;
  reg [0:0] q2_2;
  reg h3;
  reg t3;
  wire r3;
  wire push3;
  wire pop3;
  reg [255:0] d3_0;
  reg [255:0] q3_0;
  reg [6:0] d3_1;
  reg [6:0] q3_1;
  reg [0:0] d3_2;
  reg [0:0] q3_2;
  reg h4;
  reg t4;
  wire r4;
  wire push4;
  wire pop4;
  reg [255:0] d4_0;
  reg [255:0] q4_0;
  reg [6:0] d4_1;
  reg [6:0] q4_1;
  reg [0:0] d4_2;
  reg [0:0] q4_2;
  reg h5;
  reg t5;
  wire r5;
  wire push5;
  wire pop5;
  reg [255:0] d5_0;
  reg [255:0] q5_0;
  reg [6:0] d5_1;
  reg [6:0] q5_1;
  reg [0:0] d5_2;
  reg [0:0] q5_2;
  reg h6;
  reg t6;
  wire r6;
  wire push6;
  wire pop6;
  reg [255:0] d6_0;
  reg [255:0] q6_0;
  reg [6:0] d6_1;
  reg [6:0] q6_1;
  reg [0:0] d6_2;
  reg [0:0] q6_2;
  reg h7;
  reg t7;
  wire r7;
  wire push7;
  wire pop7;
  reg [255:0] d7_0;
  reg [255:0] q7_0;
  reg [6:0] d7_1;
  reg [6:0] q7_1;
  reg [0:0] d7_2;
  reg [0:0] q7_2;
  assign r0 = (rst_n && (!t0));
  assign push0 = (i_valid && r0);
  assign pop0 = (h0 && r1);
  assign r1 = (rst_n && (!t1));
  assign push1 = (h0 && r1);
  assign pop1 = (h1 && r2);
  assign r2 = (rst_n && (!t2));
  assign push2 = (h1 && r2);
  assign pop2 = (h2 && r3);
  assign r3 = (rst_n && (!t3));
  assign push3 = (h2 && r3);
  assign pop3 = (h3 && r4);
  assign r4 = (rst_n && (!t4));
  assign push4 = (h3 && r4);
  assign pop4 = (h4 && r5);
  assign r5 = (rst_n && (!t5));
  assign push5 = (h4 && r5);
  assign pop5 = (h5 && r6);
  assign r6 = (rst_n && (!t6));
  assign push6 = (h5 && r6);
  assign pop6 = (h6 && r7);
  assign r7 = (rst_n && (!t7));
  assign push7 = (h6 && r7);
  assign pop7 = (h7 && o_ready);
  assign i_ready = r0;
  assign o_valid = (rst_n && h7);
  assign o_0 = (o_valid ? d7_0 : 256'd0);
  assign o_1 = (o_valid ? d7_1 : 7'd0);
  assign o_2 = (o_valid ? d7_2 : 1'd0);
  always_ff @(posedge clk or negedge rst_n)
    if ((!rst_n))
      begin
        h0 <= 1'd0;
        t0 <= 1'd0;
        d0_0 <= 256'd0;
        q0_0 <= 256'd0;
        d0_1 <= 7'd0;
        q0_1 <= 7'd0;
        d0_2 <= 1'd0;
        q0_2 <= 1'd0;
        h1 <= 1'd0;
        t1 <= 1'd0;
        d1_0 <= 256'd0;
        q1_0 <= 256'd0;
        d1_1 <= 7'd0;
        q1_1 <= 7'd0;
        d1_2 <= 1'd0;
        q1_2 <= 1'd0;
        h2 <= 1'd0;
        t2 <= 1'd0;
        d2_0 <= 256'd0;
        q2_0 <= 256'd0;
        d2_1 <= 7'd0;
        q2_1 <= 7'd0;
        d2_2 <= 1'd0;
        q2_2 <= 1'd0;
        h3 <= 1'd0;
        t3 <= 1'd0;
        d3_0 <= 256'd0;
        q3_0 <= 256'd0;
        d3_1 <= 7'd0;
        q3_1 <= 7'd0;
        d3_2 <= 1'd0;
        q3_2 <= 1'd0;
        h4 <= 1'd0;
        t4 <= 1'd0;
        d4_0 <= 256'd0;
        q4_0 <= 256'd0;
        d4_1 <= 7'd0;
        q4_1 <= 7'd0;
        d4_2 <= 1'd0;
        q4_2 <= 1'd0;
        h5 <= 1'd0;
        t5 <= 1'd0;
        d5_0 <= 256'd0;
        q5_0 <= 256'd0;
        d5_1 <= 7'd0;
        q5_1 <= 7'd0;
        d5_2 <= 1'd0;
        q5_2 <= 1'd0;
        h6 <= 1'd0;
        t6 <= 1'd0;
        d6_0 <= 256'd0;
        q6_0 <= 256'd0;
        d6_1 <= 7'd0;
        q6_1 <= 7'd0;
        d6_2 <= 1'd0;
        q6_2 <= 1'd0;
        h7 <= 1'd0;
        t7 <= 1'd0;
        d7_0 <= 256'd0;
        q7_0 <= 256'd0;
        d7_1 <= 7'd0;
        q7_1 <= 7'd0;
        d7_2 <= 1'd0;
        q7_2 <= 1'd0;
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
        h2 <= (t2 || ((h2 && (!pop2)) || push2));
        t2 <= ((!pop2) && (t2 || (h2 && push2)));
        if ((pop2 && t2))
          d2_0 <= q2_0;
        else
          if ((push2 && ((!h2) || pop2)))
            d2_0 <= d1_0;
        if ((push2 && (h2 && (!pop2))))
          q2_0 <= d1_0;
        if ((pop2 && t2))
          d2_1 <= q2_1;
        else
          if ((push2 && ((!h2) || pop2)))
            d2_1 <= d1_1;
        if ((push2 && (h2 && (!pop2))))
          q2_1 <= d1_1;
        if ((pop2 && t2))
          d2_2 <= q2_2;
        else
          if ((push2 && ((!h2) || pop2)))
            d2_2 <= d1_2;
        if ((push2 && (h2 && (!pop2))))
          q2_2 <= d1_2;
        h3 <= (t3 || ((h3 && (!pop3)) || push3));
        t3 <= ((!pop3) && (t3 || (h3 && push3)));
        if ((pop3 && t3))
          d3_0 <= q3_0;
        else
          if ((push3 && ((!h3) || pop3)))
            d3_0 <= d2_0;
        if ((push3 && (h3 && (!pop3))))
          q3_0 <= d2_0;
        if ((pop3 && t3))
          d3_1 <= q3_1;
        else
          if ((push3 && ((!h3) || pop3)))
            d3_1 <= d2_1;
        if ((push3 && (h3 && (!pop3))))
          q3_1 <= d2_1;
        if ((pop3 && t3))
          d3_2 <= q3_2;
        else
          if ((push3 && ((!h3) || pop3)))
            d3_2 <= d2_2;
        if ((push3 && (h3 && (!pop3))))
          q3_2 <= d2_2;
        h4 <= (t4 || ((h4 && (!pop4)) || push4));
        t4 <= ((!pop4) && (t4 || (h4 && push4)));
        if ((pop4 && t4))
          d4_0 <= q4_0;
        else
          if ((push4 && ((!h4) || pop4)))
            d4_0 <= d3_0;
        if ((push4 && (h4 && (!pop4))))
          q4_0 <= d3_0;
        if ((pop4 && t4))
          d4_1 <= q4_1;
        else
          if ((push4 && ((!h4) || pop4)))
            d4_1 <= d3_1;
        if ((push4 && (h4 && (!pop4))))
          q4_1 <= d3_1;
        if ((pop4 && t4))
          d4_2 <= q4_2;
        else
          if ((push4 && ((!h4) || pop4)))
            d4_2 <= d3_2;
        if ((push4 && (h4 && (!pop4))))
          q4_2 <= d3_2;
        h5 <= (t5 || ((h5 && (!pop5)) || push5));
        t5 <= ((!pop5) && (t5 || (h5 && push5)));
        if ((pop5 && t5))
          d5_0 <= q5_0;
        else
          if ((push5 && ((!h5) || pop5)))
            d5_0 <= d4_0;
        if ((push5 && (h5 && (!pop5))))
          q5_0 <= d4_0;
        if ((pop5 && t5))
          d5_1 <= q5_1;
        else
          if ((push5 && ((!h5) || pop5)))
            d5_1 <= d4_1;
        if ((push5 && (h5 && (!pop5))))
          q5_1 <= d4_1;
        if ((pop5 && t5))
          d5_2 <= q5_2;
        else
          if ((push5 && ((!h5) || pop5)))
            d5_2 <= d4_2;
        if ((push5 && (h5 && (!pop5))))
          q5_2 <= d4_2;
        h6 <= (t6 || ((h6 && (!pop6)) || push6));
        t6 <= ((!pop6) && (t6 || (h6 && push6)));
        if ((pop6 && t6))
          d6_0 <= q6_0;
        else
          if ((push6 && ((!h6) || pop6)))
            d6_0 <= d5_0;
        if ((push6 && (h6 && (!pop6))))
          q6_0 <= d5_0;
        if ((pop6 && t6))
          d6_1 <= q6_1;
        else
          if ((push6 && ((!h6) || pop6)))
            d6_1 <= d5_1;
        if ((push6 && (h6 && (!pop6))))
          q6_1 <= d5_1;
        if ((pop6 && t6))
          d6_2 <= q6_2;
        else
          if ((push6 && ((!h6) || pop6)))
            d6_2 <= d5_2;
        if ((push6 && (h6 && (!pop6))))
          q6_2 <= d5_2;
        h7 <= (t7 || ((h7 && (!pop7)) || push7));
        t7 <= ((!pop7) && (t7 || (h7 && push7)));
        if ((pop7 && t7))
          d7_0 <= q7_0;
        else
          if ((push7 && ((!h7) || pop7)))
            d7_0 <= d6_0;
        if ((push7 && (h7 && (!pop7))))
          q7_0 <= d6_0;
        if ((pop7 && t7))
          d7_1 <= q7_1;
        else
          if ((push7 && ((!h7) || pop7)))
            d7_1 <= d6_1;
        if ((push7 && (h7 && (!pop7))))
          q7_1 <= d6_1;
        if ((pop7 && t7))
          d7_2 <= q7_2;
        else
          if ((push7 && ((!h7) || pop7)))
            d7_2 <= d6_2;
        if ((push7 && (h7 && (!pop7))))
          q7_2 <= d6_2;
      end
endmodule

