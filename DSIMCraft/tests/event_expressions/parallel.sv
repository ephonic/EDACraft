`timescale 1ns/1ps
module lane #(parameter INDEX=1,PERIOD=1)(output integer count,output logic error);
 logic[7:0]bus;
 initial begin bus=0;repeat(4)begin #PERIOD;bus[INDEX]=~bus[INDEX];end end
 initial begin count=0;error=0;#0;repeat(4)begin @(bus[INDEX]);count++;if(count>4)error=1;end end
endmodule
module top;
 integer a,b;logic ea,eb;
 lane #(1,1)left(a,ea);lane #(5,2)right(b,eb);
endmodule
