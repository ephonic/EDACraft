`timescale 1ns/1ps
module top;
  logic signed [7:0] a=-7,b=11;
  logic [12:0] u=13'h1ffd;
  logic [63:0] w=64'hffeeddccbb009988;
  logic signed [31:0] s=-123;
  logic [31:0] x=32'h01xx00zz;
  logic [63:0] out0,out1,out2,out3,out4,out5;
  integer i;
  initial begin
    for(i=0;i<70;i=i+1) begin
      out0=(a+b)*(a-8'sd3);
      out1=(u+13'd17)^(w>>i);
      out2=((a<b)&&(s<0))|((a+8'sd1)>b);
      out3=~((x&32'hff00ff00)^(x>>i));
      out4=(w<<(i-1))+(u*13'd9);
      out5=$unsigned(a+b)+$signed(u-13'd7);
      $display("TRACE expr %0d %h %h %h %h %h %h",i,out0,out1,out2,out3,out4,out5);
      #1;
      a=a*8'sd3-8'sd7;b=b+8'sd13;u=u+13'd37;
      w=w*64'd6364136223846793005+64'd1442695040888963407;
      if(i==7)x=32'h12345678;
      if(i==31)x=32'hz000000x;
    end
    $finish;
  end
endmodule
