`timescale 1ns/1ps
module lane #(parameter STEP=1)(output logic[31:0] result,output logic error);
logic[64:0] bits_value;int i=0;
initial begin
 bits_value=0;result=0;error=0;
 repeat(5)begin
  #STEP bits_value=(65'b1<<(i*13));
  result=$countones(bits_value)*100+$clog2(i+1)*10+$onehot(bits_value);
  if($isunknown(bits_value)||!$onehot0(bits_value))error=1;
  i++;
 end
end
endmodule
module top;
wire[31:0] a,b;wire ea,eb;
lane #(.STEP(2)) u(.result(a),.error(ea));lane #(.STEP(3)) v(.result(b),.error(eb));
endmodule
