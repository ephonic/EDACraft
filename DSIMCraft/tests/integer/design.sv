`timescale 1ns/1ps
module top;
integer i, total, divided, remainder, shifted;
integer initialized=-7;
reg signed [63:0] extended;
reg [31:0] bits;
initial begin
  $display("TRACE initial %h %0d",i,initialized);
  total=0;
  for(i=-3;i<4;i=i+1) begin
    total=total+i*i;
    #1;
  end
  divided=-19/4; remainder=-19%4; shifted=-128>>>3;
  extended=initialized; bits=initialized[31:0];
  #1 $display("TRACE arithmetic %0d %0d %0d %0d %0d %h %h",i,total,divided,remainder,shifted,extended,bits);
  i=32'h7fffffff; i=i+1;
  #1 $display("TRACE overflow %0d %d",i,i);
  i=32'hxxzz1234; bits=i[23:8];
  #1 $display("TRACE four %h %h",i,bits);
  $finish;
end
endmodule
