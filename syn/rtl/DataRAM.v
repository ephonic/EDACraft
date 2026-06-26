//Data Memory in a Boolean Processor
`timescale 1ns/1ps

module DataRAM #(
    parameter Mem_Depth = 'd128,parameter C = 1'b0,parameter D = 1'b1
)
(
    input [6:0] writeaddr,readaddr1,readaddr2,readaddr3,readaddr4,
    input writedata,
    input CS,
    input SCK,
    input clk,
    output readdata1,readdata2,readdata3,readdata4,readdata5,
    output reg MISO
);

reg RegCell[0:Mem_Depth-1];
integer i;
reg Data_State=D;

//Initialize the contents of Data Memory
initial begin
    for (i=0;i<128;i=i+1) begin
        RegCell[i] = 1'b0;
    end
end

always @(posedge clk) 
if(CS==1) 
  begin
    MISO<=1'b0;
    RegCell[writeaddr] <= writedata;
  end
else begin
    RegCell[writeaddr] <= writedata;
    if (SCK == 1'b0)
    MISO <= RegCell[writeaddr];  //?
end 

assign readdata1 = RegCell[readaddr1];
assign readdata2 = RegCell[readaddr2];
assign readdata3 = RegCell[readaddr3];
assign readdata4 = RegCell[readaddr4];
assign readdata5 = RegCell[writeaddr];

endmodule //DataRAM