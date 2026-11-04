`timescale 1ns/1ps
module top;
logic[7:0]data=0;logic[3:0]index=0;logic a=0,b=0,gate=0,other=0;
integer bits_seen=0,sums=0,mixed=0,comma=0;logic[129:0]wide=0;
always @(data[index] iff gate) bits_seen++;
always @((data+wide) iff gate) sums++;
always @(posedge a iff gate or negedge b iff other) mixed++;
always @((posedge a iff gate), (negedge b iff other)) comma++;
initial begin
#1 gate=1;other=0;
#1 data=1;a=1;b=1;
#1 gate=0;other=1;b=0;wide[129]=1;
#1 gate=1;index=1;
#1 data=3;a=0;b=1;
#1 a=1;other=0;b=0;data=1;
#1 gate=0;data=0;
#1 gate=1;
#1 $display("TRACE mixed %0d %0d %0d %0d",bits_seen,sums,mixed,comma);
if(bits_seen!==4||sums!==3||mixed!==3||comma!==3)$fatal(1,"mixed mismatch");$finish;
end
endmodule
