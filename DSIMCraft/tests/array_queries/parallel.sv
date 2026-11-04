`timescale 1ns/1ps
module lane #(parameter STEP=1)(output logic[31:0] result,output logic error);
logic[64:0] value;logic control;int i=0,dimension=1;integer bound;
logic[7:3] mem[2:4];
initial begin
 value=0;control=0;result=0;error=0;
 repeat(5)begin
  #STEP value=(65'b1<<(i*13));control=1;
  bound=$left(mem,dimension);
  result=$countbits(value,control)*100+$size(mem,2)*10+bound;
  if($dimensions(mem)!=2||$unpacked_dimensions(mem)!=1||$countbits(value,1'bx,1'bz)!=0)error=1;
  dimension=3-dimension;i++;
 end
end
endmodule
module top;
wire[31:0] a,b;wire ea,eb;
lane #(.STEP(2)) u(.result(a),.error(ea));lane #(.STEP(3)) v(.result(b),.error(eb));
endmodule
