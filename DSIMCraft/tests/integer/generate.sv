`timescale 1ns/1ps
module top;
genvar g;
for(g=0;g<2;g=g+1)begin : lanes
  integer index=0;
  integer total=10;
  reg [7:0] packed_value=0;
  initial begin : step
    integer temporary;
    temporary=-2;
    repeat(3)begin
      #1;
      temporary=temporary-1;
      total=total+temporary+g;
      packed_value[index]=1;
      index=index+1;
    end
    $display("TRACE generated %0d %0d %0d %h",g,temporary,total,packed_value);
  end
end
initial begin #5 $finish; end
endmodule
