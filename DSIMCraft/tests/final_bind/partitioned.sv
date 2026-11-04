`timescale 1ns/1ps
module lane #(parameter ID=1)(output integer result);
 initial begin result=0;#0.5;result=ID;#1;result=ID+1;end
 final result=result+10;
endmodule
module top;
 wire[31:0]a,b;
 lane #(1)u(a);lane #(2)v(b);
 initial begin #3;$finish;end
endmodule
