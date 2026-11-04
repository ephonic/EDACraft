`timescale 1ns/1ps
module lane #(parameter int BASE=3,parameter int D=2)(output logic[63:0] q,output logic error);
typedef enum byte {FIRST=2,SECOND=7,THIRD=-3,LAST=1} E;
E e;integer i;
initial begin
error=0;e=FIRST;
for(i=0;i<8;i++)begin
q=64'(BASE*(i+1));e=e.next();#D;
end
if(e!==FIRST||e.num()!==4)error=1;
end
endmodule
module top;
wire[63:0] a,b;wire ea,eb;
lane #(.BASE(3),.D(2))u(a,ea);lane #(.BASE(7),.D(3))v(b,eb);
initial #25 $finish;
endmodule
