`timescale 1ns/1ps
module top;
 integer a[2:0]='{10,20,30};
 integer b[0:1][1:0]='{default:'{default:0}};
 integer row=0,source=7;
 logic[1:0][7:0] p='{'0,'0};
 initial begin
  #1;a<='{a[1],a[0],a[2]};p<=#2 '{8'ha5,8'hc3};
  b[row]<=#2 '{source,source+1};row=1;source=99;
  #1;$display("TRACE nba %0d %0d %0d %h",a[2],a[1],a[0],p);
  #2;$display("TRACE delayed %0d %0d %0d %0d %h",b[0][1],b[0][0],b[1][1],b[1][0],p);
  a=#2 '{a[0],a[2],source};
  $display("TRACE blocking %0d %0d %0d",a[2],a[1],a[0]);
 end
 initial begin
  #5;source=123;a[0]=555;
 end
 initial begin
  #7;$display("TRACE final %0d %0d %0d %0d",a[2],a[1],a[0],source);
 end
endmodule
