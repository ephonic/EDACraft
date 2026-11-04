`timescale 1ns/1ps
module top;
 logic[129:0] a[2],d[],z[1]='{'z};
 logic[129:0] ss,pp,aa,oo,xx,ds,zs,zp,za,zo,zx;integer narrow;
 initial begin
  a[0]=130'h300000000000000010000000000000001;a[1]=3;
  d=new[2];d[0]=a[0];d[1]=a[1];
  ss=a.sum with(130'(item));pp=a.product with(item);aa=a.and with(item);oo=a.or with(item);xx=a.xor with(item);
  ds=d.sum(x) with(x+130'd1);narrow=a.sum with(int'(item));
  zs=z.sum with(item);zp=z.product with(item);za=z.and with(item);zo=z.or with(item);zx=z.xor with(item);
  #1;$display("TRACE wide %h %h %h %h %h %h %h",ss,pp,aa,oo,xx,ds,narrow);
  $display("TRACE wide-z %h %h %h %h %h",zs,zp,za,zo,zx);
  a[0]='x;a[1]=0;aa=a.and with(item);oo=a.or with(item);xx=a.xor with(item);
  #1;$display("TRACE wide-x %h %h %h",aa,oo,xx);
 end
endmodule
