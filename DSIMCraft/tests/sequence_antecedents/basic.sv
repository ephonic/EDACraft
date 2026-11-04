`timescale 1ns/1ps
module top;
reg clk=0,a=1,b=1,c=1,d=1;
integer tick=0,op=0,of=0,np=0,nf=0,rp=0,rf=0,covered=0,sp=0,sf=0;
always #5 clk=~clk;
assert property(@(posedge clk) a ##1 b |-> c) op++;else of++;
assume property(@(posedge clk) pair() |=> c) np++;else nf++;
assert property(@(posedge clk) (a ##0 b)[*2] |-> c ##1 d) rp++;else rf++;
cover property(@(posedge clk) pair |-> c) covered++;
assert property(@(posedge clk) a |-> c) sp++;else sf++;
sequence pair; a ##1 b;endsequence
initial begin
{a,b,c,d}=4'b1111;
repeat(16)begin
#7;$display("TRACE antecedent %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",tick,op,of,np,nf,rp,rf,covered,sp,sf);
#3;tick++;case(tick)
1:{a,b,c,d}=4'b1101;
2:{a,b,c,d}=4'b0110;
3:{a,b,c,d}=4'b1011;
4:{a,b,c,d}=4'b1101;
5:{a,b,c,d}=4'b1111;
6:{a,b,c,d}=4'b1110;
7:{a,b,c,d}=4'b0111;
8:{a,b,c,d}=4'bx111;
9:{a,b,c,d}=4'bz111;
10:{a,b,c,d}=4'b1011;
11:{a,b,c,d}=4'b1101;
12:{a,b,c,d}=4'b1111;
13:{a,b,c,d}=4'b0110;
14:{a,b,c,d}=4'b1101;
15:{a,b,c,d}=4'b1111;
default:a=0;endcase
end
#1;$finish;end
endmodule
