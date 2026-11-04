`timescale 1ns/1ps
module top;
 logic[7:0] a[2:0]='{8'hff,2,3};logic signed[7:0] b[3]='{-1,2,3};
 integer item=99,sum,named,predicate,signed_sum,product,width,bias=1;
 logic[15:0] aa,oo,xx;logic[7:0] sub;integer nested,shadow,filtered;
 integer c[2]='{1,2};logic[15:8] shifted[2]='{8'h12,8'h34};bit flags[2]='{1,0};integer selected,invalid_bit;
 initial begin
  sum=a.sum() with(int'(item));named=a.sum(x) with(int'(x));predicate=a.sum with(item>1);
  signed_sum=b.sum with(int'(item));product=a.product with(16'(item));width=$bits(a.sum with(int'(item)));
  aa=a.and with(16'(item)|16'hf000);oo=a.or(x) with(16'(x)<<4);xx=a.xor with(16'(item));
  sub=a.sum with(item[3:0]);nested=c.sum(x) with(c.sum(y) with(x*y+bias));
  shadow=c.sum(x) with(c.sum(x) with(x));filtered=a.sum with(item>2?32'(item):32'd0);
  selected=shifted.sum with(int'(item[11:8]));invalid_bit=flags.sum with(item[9]);
  #1;$display("TRACE values %0d %0d %0d %0d %0d %0d %0d %h %h %h %h %0d %0d %0d %0d %0d",sum,named,predicate,signed_sum,product,width,item,aa,oo,xx,sub,nested,shadow,filtered,selected,invalid_bit);
 end
endmodule
