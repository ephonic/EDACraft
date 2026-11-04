`timescale 1ps/1ps
module top;
 int q[$],a[int unsigned];int unsigned key;int one=0,two=0;
 initial begin
  q='{1,7};a[0]=2;a[-1]=9;
  #2;one=q[$];a.last(key);
  #2;q[$]=a[key];one=q[$];
 end
 initial begin #1;two=11;#2;two=23;end
endmodule
