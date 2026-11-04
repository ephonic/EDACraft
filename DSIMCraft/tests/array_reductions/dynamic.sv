`timescale 1ns/1ps
module top;
 logic[7:0] a[];
 logic signed[7:0] b[];
 logic[7:0] sums,products,ands,ors,xors;
 integer signed_sum,signed_product;
 task sample();
  sums=a.sum();products=a.product();ands=a.and();ors=a.or();xors=a.xor();
  $display("TRACE dynamic %h %h %h %h %h",sums,products,ands,ors,xors);
 endtask
 initial begin
  sample();#1;a=new[1];a[0]='z;sample();
  #1;a=new[3];a[0]=8'hff;a[1]=2;a[2]=3;sample();
  b=new[3];b[0]=-1;b[1]=2;b[2]=3;signed_sum=b.sum();signed_product=b.product();
  $display("TRACE signed %0d %0d",signed_sum,signed_product);
  #1;a=new[4](a);a[3]=4;sample();
  #1;a.delete();sample();
 end
endmodule
