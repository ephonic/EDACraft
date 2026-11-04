`timescale 1ns/1ps
module lane #(parameter STEP=3,PERIOD=2)(output integer q,output logic error);
 event start,done;integer k;
 initial begin q=0;error=0;
   for(k=0;k<4;k++)begin #PERIOD;->>start;@done;q+=STEP;end
   if(q!==4*STEP)error=1;
 end
 initial repeat(4)begin @start;#1;->done;end
endmodule
module top;
 integer a,b;logic ea,eb;
 lane #(3,2)left(a,ea);lane #(7,3)right(b,eb);
endmodule
