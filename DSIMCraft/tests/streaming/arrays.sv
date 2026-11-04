`timescale 1ns/1ps
module top;
 logic[7:0] a[2:0]='{8'h12,8'h34,8'h56};
 logic[7:0] b[0:1][3:2]='{'{8'h78,8'h9a},'{8'hbc,8'hde}};
 logic[7:0] dst[0:2];
 logic[31:0] flat;
 logic[15:0] row;
 initial begin
  flat={>>{a,8'hf0}};row={<<8{b[1]}};
  {>>{dst}}={<<8{a}};
  #1;$display("TRACE arrays %h %h %h %h %h",flat,row,dst[0],dst[1],dst[2]);
  {<<4{a}}=24'habcd12;
  {>>{b[0],b[1]}}=32'h01234567;
  #1;$display("TRACE unpack %h %h %h %h %h %h %h",a[2],a[1],a[0],b[0][3],b[0][2],b[1][3],b[1][2]);
 end
endmodule
