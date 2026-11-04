`timescale 1ns/1ps
module lane #(parameter BASE=1)(output logic[15:0] q);
 integer a[2]='{BASE,BASE+1};
 logic[1:0][7:0] packed_value;
 initial begin
  packed_value='{8'h74,8'h00};q=packed_value;
  #1;a='{a[1],a[0]};packed_value='{8'h74,8'h01};q=packed_value;
  #2;a<=#1 '{default:BASE+2};
  #2;packed_value='{8'h74,8'h03};q=packed_value;
 end
endmodule
module top;
 wire[15:0] one,two;
 lane #(.BASE(3)) u(one);lane #(.BASE(7)) v(two);
endmodule
