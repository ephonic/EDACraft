`timescale 1ns/1ps
module top;
 logic[129:0] a[2],b[],z[1]='{'z};
 bit[129:0] c[2]='{'1,2};
 logic[129:0] ss,pp,aa,oo,xx,ds,dp,da,do_,dx,zs,zp,za,zo,zx,bs;
 initial begin
  a[0]=130'h300000000000000010000000000000001;a[1]=3;
  b=new[2];b[0]=a[0];b[1]=a[1];
  ss=a.sum();pp=a.product();aa=a.and();oo=a.or();xx=a.xor();
  ds=b.sum();dp=b.product();da=b.and();do_=b.or();dx=b.xor();bs=c.sum();
  zs=z.sum();zp=z.product();za=z.and();zo=z.or();zx=z.xor();
  #1;$display("TRACE wide %h %h %h %h %h %h %h %h %h %h %h",ss,pp,aa,oo,xx,ds,dp,da,do_,dx,bs);
  $display("TRACE wide-z %h %h %h %h %h",zs,zp,za,zo,zx);
  a[0]='x;a[1]=0;ss=a.sum();pp=a.product();aa=a.and();oo=a.or();xx=a.xor();
  #1;$display("TRACE wide-x %h %h %h %h %h",ss,pp,aa,oo,xx);
 end
endmodule
