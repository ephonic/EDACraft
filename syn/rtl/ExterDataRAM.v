//Data Memory in a Boolean Processor
`timescale 1ns/1ps

module ExterDataRAM #(
    parameter Mem_Depth = 'd128
)
(
    input [6:0] writeaddr,readaddr1,readaddr2,readaddr3,readaddr4,
    input writedata,
    input clk,
    output readdata1,readdata2,readdata3,readdata4
);
         
reg RegCell[0:Mem_Depth-1];
integer i;

//Initialize the contents of Data Memory
initial begin
    for (i=0;i<128;i=i+1) begin
        RegCell[i] = 1'b1;
    end      
end

always @(posedge clk) begin
    RegCell[writeaddr] <= writedata;
end

assign readdata1=RegCell[readaddr1];
assign readdata2=RegCell[readaddr2];
assign readdata3=RegCell[readaddr3];
assign readdata4=RegCell[readaddr4];

endmodule //DataRAM
