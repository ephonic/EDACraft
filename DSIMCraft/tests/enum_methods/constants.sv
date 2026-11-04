`timescale 1ns/1ps
module lane #(parameter int WIDTH=4)(output logic[31:0] q);
typedef enum logic[WIDTH-1:0] {FIRST=1,SECOND=3,LAST=5} E;
parameter E P=FIRST.next(2);
parameter N=FIRST.num();
parameter E R=P.prev();
localparam int BITS=$bits(E);
E e;
initial begin
e=R;q=N+BITS+e;
if(e!==SECOND||P!==LAST||N!==3||BITS!==WIDTH)$fatal(1,"constant methods");
#1;e=e.first.next(2).prev; q+=e;
if(e!==SECOND)$fatal(1,"chain");
end
endmodule
module top;
wire[31:0] a,b;
lane #(.WIDTH(4))u(a);lane #(.WIDTH(9))v(b);
for(genvar g=0;g<2;g=g+1)begin:gen
 typedef enum logic[g+2:0] {A=1,B=2,C=3} T;
 parameter T P=A.next(g+1);
 T e;
 initial begin e=P;#2;e=e.prev(g+1);if(e!==A)$fatal(1,"generate binding");end
end
initial begin #3;$display("TRACE constants %0d %0d",a,b);end
endmodule
