//ProgramCounter in a Boolean Processor
`timescale 1ns / 1ps
module ProgramCounter #(
    parameter Addr_Width = 'd7                   //Depth of PC and Data Memory in Boolean Processor is 512, so Addr_Width is log2(512) ~ 'd9
) (
    input                       clk,
    input                       rst,
    input                       flag,
    input      [Addr_Width-1:0] pc,
    input                       jump_flag,  //Execute the last instruction, pc_addr jump to 0 
    output reg [Addr_Width-1:0] PC_Addr
);
  //reg [Addr_Width-1:0] PC_Addr;                 //7bit PC_Address,every positive clk PC_Addr++

  always @(posedge clk or posedge rst) begin
    if (rst) begin
      if (!flag) PC_Addr <= pc;
      else PC_Addr <= 0;
    end else if (jump_flag) PC_Addr <= 0;
    else if (flag) PC_Addr <= PC_Addr + 1;
  end



endmodule
