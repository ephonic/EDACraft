`timescale 1ns/1ps
module pieces(input [7:0] d,output [7:0] y);
 assign y=d;
endmodule
module scalar(input d,output y);
 assign y=d;
endmodule
module top;
 logic [7:0] d;
 logic [15:4] p;
 wire [7:0] n;
 logic [7:0] mixed;
 logic [7:0] split;
 logic single;
 logic [3:0] repeated;
 integer ignored;
 function integer upper();begin split[7:4]=4'hc;upper=0;end endfunction
 pieces a(d,{p[15:12],p[7:4]});
 pieces b(d,{n[7:4],mixed[3:0]});
 scalar c(d[1],single);
 pieces r(d,{repeated,repeated});
 scalar s0(d[0],split[0]);
 scalar s1(d[1],split[1]);
 scalar s2(d[2],split[2]);
 scalar s3(d[3],split[3]);
 initial begin
  p[11:8]=4'h5;mixed[7:4]=4'ha;ignored=upper();d=8'h96;
  #1 $display("TRACE parts %h %b %h %h %b",p,n,mixed,split,single);
  if(repeated!==d[3:0])$fatal(1,"repeated concatenation");
  if(p!==12'h956||n!==8'b1001zzzz||mixed!==8'ha6||split!==8'hc6||single!==1)$fatal(1,"parts first");
  p[11:8]<=4'h3;d<=8'h2b;
  #1 $display("TRACE parts %h %b %h %h %b",p,n,mixed,split,single);
  if(repeated!==d[3:0])$fatal(1,"repeated concatenation");
  if(p!==12'h23b||n!==8'b0010zzzz||mixed!==8'hab||split!==8'hcb||single!==1)$fatal(1,"parts final");
  $finish;
 end
endmodule
