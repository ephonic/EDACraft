`timescale 1ns/1ps
module top;
 logic signed[7:0] a[];integer bias=1;
 integer ss,pp,aa,oo,xx;
 task sample();
  ss=a.sum with(int'(item)+bias);pp=a.product(x) with(int'(x));
  aa=a.and with(int'(item));oo=a.or with(int'(item));xx=a.xor with(int'(item));
  $display("TRACE dynamic %h %h %h %h %h",ss,pp,aa,oo,xx);
 endtask
 initial begin
  sample();#1;a=new[1];a[0]='z;sample();
  #1;a=new[3];a[0]=-1;a[1]=2;a[2]=3;sample();
  #1;a=new[4](a);a[3]=4;bias=2;sample();
  #1;a.delete();sample();
 end
endmodule
