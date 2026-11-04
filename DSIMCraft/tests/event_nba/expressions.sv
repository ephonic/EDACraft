`timescale 1ns/1ps
module top;
logic[3:0]a=0,b=0;logic g=0;integer q=0,r=0,t=0;
function automatic logic positive(input logic[3:0]v);return v>2;endfunction
initial begin q<=@(a+b)11;r<=repeat(2)@(posedge positive(a) iff g)22;t<=@(a[1] or b[2])33;
#1 a=1;#1;$display("TRACE expr1 %0d %0d %0d",q,r,t);
g=1;a=4;#1;a=0;#1;a=4;#1;$display("TRACE expr2 %0d %0d %0d",q,r,t);
b=4;#1;$display("TRACE expr3 %0d %0d %0d",q,r,t);if(q!==11||r!==22||t!==33)$fatal(1,"expression NBA mismatch");$finish;end
endmodule
