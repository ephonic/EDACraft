`timescale 1ns/1ps
module top;
 logic[95:0] a[],b[];
 bit[7:0] c[];
 logic[95:0] qa=0,qb=0;
 logic[7:0] q=0;
 integer i=0;
 initial begin
  a=new[1];b=new[1];c=new[1];
  {a[0],b[0],c[0]}={96'h123456789abcdef001234567,96'hfedcba987654321001234567,8'bxz101001};
  {a[0][80+:12],b[0][7:0],q}=28'habcdef1;
  qa=a[0];qb=b[0];
  $display("TRACE wide %h %h %h %h",qa,qb,c[0],q);
  i='x;{a[i],c[0],q}=112'hffffffffffffffffffffffff5a73;
  qa=a[0];$display("TRACE invalid %h %h %h",qa,c[0],q);
  #1;$finish;
 end
endmodule
