`timescale 1ns/1ps
module tb_compare;
 reg [0:0] clk_c0;
 reg [0:0] clk_c1;
 reg [0:0] rst_r0;
 reg [0:0] rst_r1;
 reg [12:0] in_x;
 reg [0:0] in_en;
 wire [12:0] out_state0;
 wire [12:0] out_state1;
 wire [12:0] out_shifted;
 agent_event_module dut(.clk_c0(clk_c0),.clk_c1(clk_c1),.rst_r0(rst_r0),.rst_r1(rst_r1),.in_x(in_x),.in_en(in_en),.out_state0(out_state0),.out_state1(out_state1),.out_shifted(out_shifted));
 reg [17:0] vectors [0:1583];
 integer event_index;
 initial begin
 $readmemh("stimulus.hex", vectors);
 for (event_index=0; event_index<1584; event_index=event_index+1) begin
 in_x=vectors[event_index][16:4];
 in_en=vectors[event_index][17:17];
 #1;
 clk_c0=vectors[event_index][0:0];
 clk_c1=vectors[event_index][1:1];
 rst_r0=vectors[event_index][2:2];
 rst_r1=vectors[event_index][3:3];
 #3;
 if (event_index>=2) $display("RTL_DUAL_TRACE %0d state0=%b state1=%b shifted=%b",event_index-2,out_state0,out_state1,out_shifted);
 end
 $display("RTL_DUAL_DONE events=1582 outputs=3");
 $finish;
 end
endmodule
