`timescale 1ns/1ps
module top;
integer a[],idx=0,rhs=7,calls=0,phase=0,first=0,middle=0;
logic signed[95:0] wide[];bit[7:0] clean[];
function integer address();calls++;return idx;endfunction
initial begin
 a=new[2];a[0]=0;a[1]=0;wide=new[1];wide[0]=0;clean=new[1];clean[0]=0;
 a[address()]<=#3 rhs;a[1]<=rhs+1;a[1]<=#0 rhs+2;
 a[0]<=#2 8;a[0]<=#2 9;
 wide[0]<=#3 -3;clean[0]<=#2 8'bx1z010x1;
 #0;phase=a[1];
 #1;first=a[1];rhs=99;idx=1;
 #1.5;middle=a[0];a[1]=20;
 #1.5;$display("TRACE sample %0d %0d %0d %0d %0d %0d %0d %h %0d",a[0],a[1],calls,phase,first,middle,rhs,wide[0],clean[0]);
end
endmodule
