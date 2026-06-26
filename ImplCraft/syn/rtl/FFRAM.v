`timescale 1ns/1ps
module FFRAM #(
    parameter Addr_Width = 'd7,
    parameter Depth = 'd128
)
(
    input clk,
    input rst,
    input jump_flag,
    input writedata,
    input [3:0] opcode,
    input [Addr_Width-1:0] readaddr1,readaddr2,readaddr3,readaddr4,                        
    output readdata1,readdata2,readdata3,readdata4
);

reg [Addr_Width-1:0]    FF_count;
reg [Depth-1:0]         Last_FF_Mem;
reg [Depth-1:0]         FF_Mem;

always @(posedge clk or posedge rst) begin
    if (rst) 
        FF_count <= 0;
    else if (jump_flag)
        FF_count <= 0;
    else if (opcode == 4'b0100)
        FF_count <= FF_count + 1;
end

//当jump_flag == 1'b1时，是否需要将FF_Mem清零？
always @(posedge clk or posedge rst) begin
    if (rst) 
        FF_Mem <= 0;
    else if (opcode == 4'b0100)
        FF_Mem[FF_count] <= writedata;
end

always @(posedge clk or posedge rst) begin
    if (rst) 
        Last_FF_Mem <= 0;
    else if (jump_flag)
        Last_FF_Mem <= FF_Mem;
end

assign readdata1 = Last_FF_Mem[readaddr1];
assign readdata2 = Last_FF_Mem[readaddr2];
assign readdata3 = Last_FF_Mem[readaddr3];
assign readdata4 = Last_FF_Mem[readaddr4];

endmodule //FFRAM