`timescale 1ns/1ps
module top;
int n,checks;
logic [7:0] q;
logic [63:0] value;
logic [7:0] mem[0:1];
function longint cv(input int a);
 cv=longint'(byte'(a));
endfunction
task sample(input int a,output byte b);
 b=8'(a+256);
endtask
initial begin
 n=255;checks=0;q=0;mem[0]=0;mem[1]=0;
 value=64'(byte'(n++));assert(n==256&&value==64'hffffffffffffffff)checks++;
 q=8'(n++ + n++);assert(n==258&&q==1)checks++;
 q=0&&int'(n++);assert(n==258)checks++;
 q=1?8'(n++):8'(n++);assert(n==259&&q==2)checks++;
 value=cv(n++);assert(n==260&&value==3)checks++;
 sample(n++,q);assert(n==261&&q==4)checks++;
 mem[0]<=#2 byte'(n++);mem[1]<=#1 8'(n++);
 #2;assert(n==263&&mem[1]==6)checks++;
 #1;assert(mem[0]==5)checks++;
 value=64'(8'(n++));
 #1;$display("TRACE effects %0d %0d %h %h",checks,n,value,q);$finish;
end
endmodule
