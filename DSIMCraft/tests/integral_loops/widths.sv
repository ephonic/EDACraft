`timescale 1ns/1ps
module top;
 logic [7:0] u=250;logic signed [7:0] a=-7;logic [63:0] w=64'hffeeddccbb009988;
 integer i;logic signed [15:0] b=0;bit [12:0] bits=13'h1ffd;
 initial begin
  for(i=-12;i<17;i++)begin u=u*8'd13+8'd9;a=a*8'sd3-8'sd7;w=w*64'd6364136223846793005+64'd1442695040888963407;bits=bits+13'd37;end
  for(i=-3;i<=3;i=i+1)b=b+(a+i);
  $display("TRACE widths %h %0d %h %h %0d %0d",u,a,w,b,bits,i);
  i=0;while(i<7)begin u=~(u^8'h73);i=i+1;end
  $display("TRACE while %h %0d",u,i);#1;$finish;
 end
endmodule
