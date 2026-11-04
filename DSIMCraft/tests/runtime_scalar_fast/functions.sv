`timescale 1ns/1ps
module top;
 function automatic [31:0] crc(input [31:0] seed);
  reg[31:0] t;integer i;
  begin
   t=seed;
   for(i=0;i<8;i=i+1)t=(t>>1)^(32'hedb88320&{32{t[0]}});
   crc=t;
  end
 endfunction
 function automatic [63:0] shifts(input [63:0] seed,input [63:0] count);
  reg[63:0] t;integer i;
  begin t=seed;for(i=0;i<3;i=i+1)t=(t<<count)^(t>>count);shifts=t;end
 endfunction
 function automatic [63:0] slices(input signed[7:0] seed);
  reg signed[7:0] t;reg[63:0] accum;integer i;
  begin t=seed;accum=0;for(i=0;i<3;i=i+1)begin accum=accum+t[7:0]+{64{t[7]}};t=t+1;end slices=accum;end
 endfunction
 reg[31:0] q;reg[63:0] a,b,c,d;integer i;
 initial begin
  q=crc(32'h12345678);$display("TRACE crc %h",q);
  q=crc(32'hzzzzzzzz);$display("TRACE z %h",q);
  q=crc(32'hxxxx0000);$display("TRACE x %h",q);
  for(i=0;i<=65;i=i+1)begin
   a=shifts(64'hfedcba9876543210,i);
   b=shifts(64'hfedcba9876543210,64'hffffffffffffffff);
   c=slices(-8'sd1);d=slices(8'sd127);
   $display("TRACE shift %0d %h %h %h %h",i,a,b,c,d);
  end
  #1;$finish;
 end
endmodule
