`timescale 1ns/1ps
module lane #(parameter STEP=3,PERIOD=2)(output integer q,output logic error);
 logic req,ack;integer k;
 initial begin req=0;q=0;error=0;
   for(k=0;k<4;k=k+1)begin #PERIOD;req=1;wait(ack);req=0;wait(!ack);q=q+STEP;end
   if(q!==4*STEP)error=1;
 end
 initial begin ack=0;repeat(4)begin wait(req);#1;ack=1;wait(!req);#1;ack=0;end end
endmodule
module top;
 integer a,b;logic ea,eb;
 lane #(3,2)left(a,ea);lane #(7,3)right(b,eb);
endmodule
