`timescale 1ns/1ps
module top;
 logic[7:0] a[2:0]='{8'hff,2,3};
 logic signed[7:0] b[0:2]='{-1,2,3};
 bit bits[3]='{1,1,1};
 logic[7:0] singleton[1]='{'z};
 logic[7:0] matrix[2][2]='{'{1,2},'{3,4}};
 integer sum,product,width,signed_sum,signed_product,bit_sum;
 logic[7:0] aa,oo,xx,zs,zp,za,zo,zx,sub;
 initial begin
  sum=a.sum();product=a.product;width=$bits(a.sum());signed_sum=b.sum();signed_product=b.product();bit_sum=bits.sum();
  aa=a.and();oo=a.or;xx=a.xor();sub=matrix[1].sum();
  zs=singleton.sum();zp=singleton.product();za=singleton.and();zo=singleton.or();zx=singleton.xor();
  #1;$display("TRACE values %0d %0d %0d %0d %0d %0d %h %h %h %h %h %h %h %h %h",sum,product,width,signed_sum,signed_product,bit_sum,aa,oo,xx,sub,zs,zp,za,zo,zx);
  a[2]='x;a[1]=0;a[0]='1;
  #1;aa=a.and();oo=a.or();xx=a.xor();sum=a.sum();
  $display("TRACE unknown %h %h %h %h",aa,oo,xx,sum);
 end
endmodule
