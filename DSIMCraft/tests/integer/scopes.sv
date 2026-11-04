`timescale 1ns/1ps
module top;
integer value=10, observed=0;
initial begin : outer
  integer value=-2;
  integer visits=2;
  reg signed [64:0] wide=-65'sd3;
  localparam STEP=3;
  repeat(3) begin : tick
    integer visits=10;
    visits=visits+1;
    value=value+STEP;
    #1;
    observed=value+visits;
    $display("TRACE scope %0d %0d %0d %h",value,visits,observed,wide);
  end
  #1;
  $display("TRACE outer %0d %0d",value,visits);
end
initial begin : other
  integer value=100;
  #2 value=value+5;
  #3 $display("TRACE sibling %0d",value);
end
initial begin
  #6 $display("TRACE module %0d %0d",value,observed);
  $finish;
end
endmodule
