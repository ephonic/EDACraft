`timescale 1ns/1ps
module top;
logic signed [95:0] a[],b[];
bit [95:0] c[];
logic [95:0] observed=0;
integer calls=0,index=0,old=0;
function automatic integer count();calls++;return 2;endfunction
function automatic integer pick();index++;return index-1;endfunction
initial begin
 a=new[count()];c=new[2];a[0]=-96'sd7;a[1]=96'h800000000000000000000005;
 old=a[pick()]++;
 b=new[3](a);a[0]=99;c[0]=96'hx01;
 observed=b[1];
 $display("TRACE elements %0d %0d %0d %0d %0d %h %h",calls,index,old,b[0],b[2]===96'bx,observed,c[0]);
 #2;index=0;b[pick()]+=3;
 $display("TRACE update %0d %0d",index,b[0]);
end
endmodule
