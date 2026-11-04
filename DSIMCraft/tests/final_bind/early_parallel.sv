`timescale 1ns/1ps
module lane #(parameter ID=1)(output integer result);
 initial begin result=0;#0.5;result=ID;#5;result=99;end
 final begin result=result+10;$display("LANE %m time=%0t result=%0d",$time,result);end
endmodule
module top;
 wire[31:0] a,b;
 lane #(1)u(a);lane #(2)v(b);
 initial begin #1;$finish;end
endmodule
