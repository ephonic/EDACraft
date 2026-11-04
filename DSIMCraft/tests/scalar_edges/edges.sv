`timescale 1ns/1ps
module top;
  reg [63:0] data, next_value;
  integer positives=0, negatives=0, changes=0;
  integer old_positive, old_negative, old_change;
  integer a,b,high,expected_positive,expected_negative,tests=0;
  always @(posedge data) positives=positives+1;
  always @(negedge data) negatives=negatives+1;
  always @(data) changes=changes+1;
  function [63:0] bits(input integer state);
    case (state)
      0: bits=64'd0;
      1: bits=64'd1;
      2: bits=64'hxxxxxxxxxxxxxxxx;
      3: bits=64'hzzzzzzzzzzzzzzzz;
    endcase
  endfunction
  initial begin
    data=0;
    for(high=0;high<2;high=high+1)
      for(a=0;a<4;a=a+1)
        for(b=0;b<4;b=b+1) begin
          data=bits(a); #1;
          old_positive=positives;old_negative=negatives;old_change=changes;
          next_value=bits(b);if(high)next_value[63]=1'b1;
          data=next_value; #1;
          expected_positive=((a==0 && b!=0)||(a>=2 && b==1));
          expected_negative=((a==1 && b!=1)||(a>=2 && b==0));
          if(positives-old_positive!=expected_positive || negatives-old_negative!=expected_negative)
            $fatal(1,"edge mismatch %d %d",a,b);
          $display("TRACE edge %0d %0d %0d %0d %0d %0d",high,a,b,positives-old_positive,negatives-old_negative,changes-old_change);
          tests=tests+1;
        end
    $display("TRACE edge complete %0d",tests);$finish;
  end
endmodule
