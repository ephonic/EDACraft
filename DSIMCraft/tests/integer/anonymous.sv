`timescale 1ns/1ps
module top;
int value=20;
reg [31:0] result=0;
initial begin
  int value=-3;
  #1;
  begin
    int value=7;
    #1 result=value;
    $display("TRACE nested %0d %0d",value,result);
  end
  #1 result=result+value;
  $display("TRACE parent %0d %0d",value,result);
end
initial begin
  int value=100;
  #4 $display("TRACE independent %0d",value);
end
initial begin
  #5 $display("TRACE top %0d %0d",value,result);
  $finish;
end
endmodule
