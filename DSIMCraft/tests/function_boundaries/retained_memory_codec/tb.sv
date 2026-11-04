`timescale 1ns/1ps
module tb_compare;
integer event_index,segment;
function [1:0] encode_h4_1;input [0:0] value;integer k;begin
for(k=0;k<1;k=k+1)begin case(value[k])
1'b0:encode_h4_1[k*2+:2]=2'b00;
1'b1:encode_h4_1[k*2+:2]=2'b01;
1'bx:encode_h4_1[k*2+:2]=2'b10;
1'bz:encode_h4_1[k*2+:2]=2'b11;
endcase end end endfunction
function [25:0] encode_h4_13;input [12:0] value;integer k;begin
for(k=0;k<13;k=k+1)begin case(value[k])
1'b0:encode_h4_13[k*2+:2]=2'b00;
1'b1:encode_h4_13[k*2+:2]=2'b01;
1'bx:encode_h4_13[k*2+:2]=2'b10;
1'bz:encode_h4_13[k*2+:2]=2'b11;
endcase end end endfunction
function [127:0] encode_h4_64;input [63:0] value;integer k;begin
for(k=0;k<64;k=k+1)begin case(value[k])
1'b0:encode_h4_64[k*2+:2]=2'b00;
1'b1:encode_h4_64[k*2+:2]=2'b01;
1'bx:encode_h4_64[k*2+:2]=2'b10;
1'bz:encode_h4_64[k*2+:2]=2'b11;
endcase end end endfunction
reg [0:0] drive_0;
reg [0:0] drive_1;
reg [0:0] drive_2;
reg [3:0] drive_3;
reg [3:0] drive_4;
reg [3:0] drive_5;
reg [3:0] drive_6;
reg [3:0] drive_7;
reg [63:0] drive_8;
reg [0:0] drive_9;
reg [0:0] drive_10;
reg [12:0] drive_11;
reg [105:0] vectors[0:7708];
reg clock_0;
wire [0:0] observed_0_0;
wire [0:0] observed_0_1;
wire [63:0] observed_0_2;
wire [12:0] observed_0_3;
dut dut_0(.clk(clock_0),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_0_0),.out_valid(observed_0_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_0_2),.out_tag(observed_0_3));
reg clock_1;
wire [0:0] observed_1_0;
wire [0:0] observed_1_1;
wire [63:0] observed_1_2;
wire [12:0] observed_1_3;
dut dut_1(.clk(clock_1),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_1_0),.out_valid(observed_1_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_1_2),.out_tag(observed_1_3));
reg clock_2;
wire [0:0] observed_2_0;
wire [0:0] observed_2_1;
wire [63:0] observed_2_2;
wire [12:0] observed_2_3;
dut dut_2(.clk(clock_2),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_2_0),.out_valid(observed_2_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_2_2),.out_tag(observed_2_3));
reg clock_3;
wire [0:0] observed_3_0;
wire [0:0] observed_3_1;
wire [63:0] observed_3_2;
wire [12:0] observed_3_3;
dut dut_3(.clk(clock_3),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_3_0),.out_valid(observed_3_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_3_2),.out_tag(observed_3_3));
reg clock_4;
wire [0:0] observed_4_0;
wire [0:0] observed_4_1;
wire [63:0] observed_4_2;
wire [12:0] observed_4_3;
dut dut_4(.clk(clock_4),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_4_0),.out_valid(observed_4_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_4_2),.out_tag(observed_4_3));
reg clock_5;
wire [0:0] observed_5_0;
wire [0:0] observed_5_1;
wire [63:0] observed_5_2;
wire [12:0] observed_5_3;
dut dut_5(.clk(clock_5),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_5_0),.out_valid(observed_5_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_5_2),.out_tag(observed_5_3));
reg clock_6;
wire [0:0] observed_6_0;
wire [0:0] observed_6_1;
wire [63:0] observed_6_2;
wire [12:0] observed_6_3;
dut dut_6(.clk(clock_6),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_6_0),.out_valid(observed_6_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_6_2),.out_tag(observed_6_3));
reg clock_7;
wire [0:0] observed_7_0;
wire [0:0] observed_7_1;
wire [63:0] observed_7_2;
wire [12:0] observed_7_3;
dut dut_7(.clk(clock_7),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_7_0),.out_valid(observed_7_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_7_2),.out_tag(observed_7_3));
reg clock_8;
wire [0:0] observed_8_0;
wire [0:0] observed_8_1;
wire [63:0] observed_8_2;
wire [12:0] observed_8_3;
dut dut_8(.clk(clock_8),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_8_0),.out_valid(observed_8_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_8_2),.out_tag(observed_8_3));
reg clock_9;
wire [0:0] observed_9_0;
wire [0:0] observed_9_1;
wire [63:0] observed_9_2;
wire [12:0] observed_9_3;
dut dut_9(.clk(clock_9),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_9_0),.out_valid(observed_9_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_9_2),.out_tag(observed_9_3));
reg clock_10;
wire [0:0] observed_10_0;
wire [0:0] observed_10_1;
wire [63:0] observed_10_2;
wire [12:0] observed_10_3;
dut dut_10(.clk(clock_10),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_10_0),.out_valid(observed_10_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_10_2),.out_tag(observed_10_3));
reg clock_11;
wire [0:0] observed_11_0;
wire [0:0] observed_11_1;
wire [63:0] observed_11_2;
wire [12:0] observed_11_3;
dut dut_11(.clk(clock_11),.rst_n(drive_0),.in_valid(drive_1),.out_ready(observed_11_0),.out_valid(observed_11_1),.in_ready(drive_2),.in_a(drive_3),.in_b(drive_4),.in_c(drive_5),.in_d(drive_6),.in_addr(drive_7),.in_data(drive_8),.in_wen(drive_9),.in_mode(drive_10),.in_tag(drive_11),.out_value(observed_11_2),.out_tag(observed_11_3));
task observe();begin case(segment)
0:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_0_0),encode_h4_1(observed_0_1),encode_h4_64(observed_0_2),encode_h4_13(observed_0_3),encode_h4_64(dut_0.words[0]),encode_h4_64(dut_0.words[1]),encode_h4_64(dut_0.words[2]),encode_h4_64(dut_0.words[3]),encode_h4_64(dut_0.words[4]),encode_h4_64(dut_0.words[5]),encode_h4_64(dut_0.words[6]),encode_h4_64(dut_0.words[7]),encode_h4_64(dut_0.words[8]),encode_h4_64(dut_0.words[9]),encode_h4_64(dut_0.words[10]),encode_h4_64(dut_0.words[11]),encode_h4_64(dut_0.words[12]),encode_h4_64(dut_0.words[13]),encode_h4_64(dut_0.words[14]),encode_h4_64(dut_0.words[15]));
1:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_1_0),encode_h4_1(observed_1_1),encode_h4_64(observed_1_2),encode_h4_13(observed_1_3),encode_h4_64(dut_1.words[0]),encode_h4_64(dut_1.words[1]),encode_h4_64(dut_1.words[2]),encode_h4_64(dut_1.words[3]),encode_h4_64(dut_1.words[4]),encode_h4_64(dut_1.words[5]),encode_h4_64(dut_1.words[6]),encode_h4_64(dut_1.words[7]),encode_h4_64(dut_1.words[8]),encode_h4_64(dut_1.words[9]),encode_h4_64(dut_1.words[10]),encode_h4_64(dut_1.words[11]),encode_h4_64(dut_1.words[12]),encode_h4_64(dut_1.words[13]),encode_h4_64(dut_1.words[14]),encode_h4_64(dut_1.words[15]));
2:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_2_0),encode_h4_1(observed_2_1),encode_h4_64(observed_2_2),encode_h4_13(observed_2_3),encode_h4_64(dut_2.words[0]),encode_h4_64(dut_2.words[1]),encode_h4_64(dut_2.words[2]),encode_h4_64(dut_2.words[3]),encode_h4_64(dut_2.words[4]),encode_h4_64(dut_2.words[5]),encode_h4_64(dut_2.words[6]),encode_h4_64(dut_2.words[7]),encode_h4_64(dut_2.words[8]),encode_h4_64(dut_2.words[9]),encode_h4_64(dut_2.words[10]),encode_h4_64(dut_2.words[11]),encode_h4_64(dut_2.words[12]),encode_h4_64(dut_2.words[13]),encode_h4_64(dut_2.words[14]),encode_h4_64(dut_2.words[15]));
3:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_3_0),encode_h4_1(observed_3_1),encode_h4_64(observed_3_2),encode_h4_13(observed_3_3),encode_h4_64(dut_3.words[0]),encode_h4_64(dut_3.words[1]),encode_h4_64(dut_3.words[2]),encode_h4_64(dut_3.words[3]),encode_h4_64(dut_3.words[4]),encode_h4_64(dut_3.words[5]),encode_h4_64(dut_3.words[6]),encode_h4_64(dut_3.words[7]),encode_h4_64(dut_3.words[8]),encode_h4_64(dut_3.words[9]),encode_h4_64(dut_3.words[10]),encode_h4_64(dut_3.words[11]),encode_h4_64(dut_3.words[12]),encode_h4_64(dut_3.words[13]),encode_h4_64(dut_3.words[14]),encode_h4_64(dut_3.words[15]));
4:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_4_0),encode_h4_1(observed_4_1),encode_h4_64(observed_4_2),encode_h4_13(observed_4_3),encode_h4_64(dut_4.words[0]),encode_h4_64(dut_4.words[1]),encode_h4_64(dut_4.words[2]),encode_h4_64(dut_4.words[3]),encode_h4_64(dut_4.words[4]),encode_h4_64(dut_4.words[5]),encode_h4_64(dut_4.words[6]),encode_h4_64(dut_4.words[7]),encode_h4_64(dut_4.words[8]),encode_h4_64(dut_4.words[9]),encode_h4_64(dut_4.words[10]),encode_h4_64(dut_4.words[11]),encode_h4_64(dut_4.words[12]),encode_h4_64(dut_4.words[13]),encode_h4_64(dut_4.words[14]),encode_h4_64(dut_4.words[15]));
5:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_5_0),encode_h4_1(observed_5_1),encode_h4_64(observed_5_2),encode_h4_13(observed_5_3),encode_h4_64(dut_5.words[0]),encode_h4_64(dut_5.words[1]),encode_h4_64(dut_5.words[2]),encode_h4_64(dut_5.words[3]),encode_h4_64(dut_5.words[4]),encode_h4_64(dut_5.words[5]),encode_h4_64(dut_5.words[6]),encode_h4_64(dut_5.words[7]),encode_h4_64(dut_5.words[8]),encode_h4_64(dut_5.words[9]),encode_h4_64(dut_5.words[10]),encode_h4_64(dut_5.words[11]),encode_h4_64(dut_5.words[12]),encode_h4_64(dut_5.words[13]),encode_h4_64(dut_5.words[14]),encode_h4_64(dut_5.words[15]));
6:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_6_0),encode_h4_1(observed_6_1),encode_h4_64(observed_6_2),encode_h4_13(observed_6_3),encode_h4_64(dut_6.words[0]),encode_h4_64(dut_6.words[1]),encode_h4_64(dut_6.words[2]),encode_h4_64(dut_6.words[3]),encode_h4_64(dut_6.words[4]),encode_h4_64(dut_6.words[5]),encode_h4_64(dut_6.words[6]),encode_h4_64(dut_6.words[7]),encode_h4_64(dut_6.words[8]),encode_h4_64(dut_6.words[9]),encode_h4_64(dut_6.words[10]),encode_h4_64(dut_6.words[11]),encode_h4_64(dut_6.words[12]),encode_h4_64(dut_6.words[13]),encode_h4_64(dut_6.words[14]),encode_h4_64(dut_6.words[15]));
7:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_7_0),encode_h4_1(observed_7_1),encode_h4_64(observed_7_2),encode_h4_13(observed_7_3),encode_h4_64(dut_7.words[0]),encode_h4_64(dut_7.words[1]),encode_h4_64(dut_7.words[2]),encode_h4_64(dut_7.words[3]),encode_h4_64(dut_7.words[4]),encode_h4_64(dut_7.words[5]),encode_h4_64(dut_7.words[6]),encode_h4_64(dut_7.words[7]),encode_h4_64(dut_7.words[8]),encode_h4_64(dut_7.words[9]),encode_h4_64(dut_7.words[10]),encode_h4_64(dut_7.words[11]),encode_h4_64(dut_7.words[12]),encode_h4_64(dut_7.words[13]),encode_h4_64(dut_7.words[14]),encode_h4_64(dut_7.words[15]));
8:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_8_0),encode_h4_1(observed_8_1),encode_h4_64(observed_8_2),encode_h4_13(observed_8_3),encode_h4_64(dut_8.words[0]),encode_h4_64(dut_8.words[1]),encode_h4_64(dut_8.words[2]),encode_h4_64(dut_8.words[3]),encode_h4_64(dut_8.words[4]),encode_h4_64(dut_8.words[5]),encode_h4_64(dut_8.words[6]),encode_h4_64(dut_8.words[7]),encode_h4_64(dut_8.words[8]),encode_h4_64(dut_8.words[9]),encode_h4_64(dut_8.words[10]),encode_h4_64(dut_8.words[11]),encode_h4_64(dut_8.words[12]),encode_h4_64(dut_8.words[13]),encode_h4_64(dut_8.words[14]),encode_h4_64(dut_8.words[15]));
9:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_9_0),encode_h4_1(observed_9_1),encode_h4_64(observed_9_2),encode_h4_13(observed_9_3),encode_h4_64(dut_9.words[0]),encode_h4_64(dut_9.words[1]),encode_h4_64(dut_9.words[2]),encode_h4_64(dut_9.words[3]),encode_h4_64(dut_9.words[4]),encode_h4_64(dut_9.words[5]),encode_h4_64(dut_9.words[6]),encode_h4_64(dut_9.words[7]),encode_h4_64(dut_9.words[8]),encode_h4_64(dut_9.words[9]),encode_h4_64(dut_9.words[10]),encode_h4_64(dut_9.words[11]),encode_h4_64(dut_9.words[12]),encode_h4_64(dut_9.words[13]),encode_h4_64(dut_9.words[14]),encode_h4_64(dut_9.words[15]));
10:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_10_0),encode_h4_1(observed_10_1),encode_h4_64(observed_10_2),encode_h4_13(observed_10_3),encode_h4_64(dut_10.words[0]),encode_h4_64(dut_10.words[1]),encode_h4_64(dut_10.words[2]),encode_h4_64(dut_10.words[3]),encode_h4_64(dut_10.words[4]),encode_h4_64(dut_10.words[5]),encode_h4_64(dut_10.words[6]),encode_h4_64(dut_10.words[7]),encode_h4_64(dut_10.words[8]),encode_h4_64(dut_10.words[9]),encode_h4_64(dut_10.words[10]),encode_h4_64(dut_10.words[11]),encode_h4_64(dut_10.words[12]),encode_h4_64(dut_10.words[13]),encode_h4_64(dut_10.words[14]),encode_h4_64(dut_10.words[15]));
11:$display("RTL_DUAL_TRACE_H4 %0d out_ready=%h out_valid=%h out_value=%h out_tag=%h _agent_mem_word_0=%h _agent_mem_word_1=%h _agent_mem_word_2=%h _agent_mem_word_3=%h _agent_mem_word_4=%h _agent_mem_word_5=%h _agent_mem_word_6=%h _agent_mem_word_7=%h _agent_mem_word_8=%h _agent_mem_word_9=%h _agent_mem_word_10=%h _agent_mem_word_11=%h _agent_mem_word_12=%h _agent_mem_word_13=%h _agent_mem_word_14=%h _agent_mem_word_15=%h",event_index,encode_h4_1(observed_11_0),encode_h4_1(observed_11_1),encode_h4_64(observed_11_2),encode_h4_13(observed_11_3),encode_h4_64(dut_11.words[0]),encode_h4_64(dut_11.words[1]),encode_h4_64(dut_11.words[2]),encode_h4_64(dut_11.words[3]),encode_h4_64(dut_11.words[4]),encode_h4_64(dut_11.words[5]),encode_h4_64(dut_11.words[6]),encode_h4_64(dut_11.words[7]),encode_h4_64(dut_11.words[8]),encode_h4_64(dut_11.words[9]),encode_h4_64(dut_11.words[10]),encode_h4_64(dut_11.words[11]),encode_h4_64(dut_11.words[12]),encode_h4_64(dut_11.words[13]),encode_h4_64(dut_11.words[14]),encode_h4_64(dut_11.words[15]));
default:$fatal(1,"invalid original case selector");endcase end endtask
initial begin
clock_0=0;
clock_1=0;
clock_2=0;
clock_3=0;
clock_4=0;
clock_5=0;
clock_6=0;
clock_7=0;
clock_8=0;
clock_9=0;
clock_10=0;
clock_11=0;
drive_0=1;
drive_1=0;
drive_2=0;
drive_3=0;
drive_4=0;
drive_5=0;
drive_6=0;
drive_7=0;
drive_8=0;
drive_9=0;
drive_10=0;
drive_11=0;
$readmemh("stimulus.hex",vectors);#1;
for(integer i=0;i<7709;i=i+1)begin
clock_0=0;
clock_1=0;
clock_2=0;
clock_3=0;
clock_4=0;
clock_5=0;
clock_6=0;
clock_7=0;
clock_8=0;
clock_9=0;
clock_10=0;
clock_11=0;
#2;
segment=vectors[i][105:102];
drive_0=vectors[i][0:0];
drive_1=vectors[i][1:1];
drive_2=vectors[i][2:2];
drive_3=vectors[i][6:3];
drive_4=vectors[i][10:7];
drive_5=vectors[i][14:11];
drive_6=vectors[i][18:15];
drive_7=vectors[i][22:19];
drive_8=vectors[i][86:23];
drive_9=vectors[i][87:87];
drive_10=vectors[i][88:88];
drive_11=vectors[i][101:89];
#2;event_index=2*i;observe();case(segment)
0:clock_0=1;
1:clock_1=1;
2:clock_2=1;
3:clock_3=1;
4:clock_4=1;
5:clock_5=1;
6:clock_6=1;
7:clock_7=1;
8:clock_8=1;
9:clock_9=1;
10:clock_10=1;
11:clock_11=1;
default:$fatal(1,"invalid clock selector");endcase
#2;event_index=2*i+1;observe();end
$display("RTL_DUAL_DONE events=15418 outputs=20");$finish;end
endmodule
