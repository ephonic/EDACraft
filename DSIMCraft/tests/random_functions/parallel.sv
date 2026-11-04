`timescale 1ns/1ps
module random_lane(output logic[15:0] out);
 integer seed=1,r;int unsigned discard;
 initial begin
  discard=$urandom(37);r=$random(seed);
  #1;r=$random(seed);#1;out=(r===32'h9c598438)?16'h7903:16'hffff;
 end
endmodule
module plain_lane(output logic[15:0] out);
 initial begin out=0;#1;out=16'h7902;#1;out=16'h7903;end
endmodule
module top;
 wire[15:0]one,two;random_lane u(one);plain_lane v(two);
endmodule
