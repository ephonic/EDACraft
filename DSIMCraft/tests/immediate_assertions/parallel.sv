`timescale 1ns/1ps
module lane #(parameter int BASE=3,parameter int DELAY=2)(output longint q,output int errs,output int hits);
localparam longint START=BASE;
initial begin:run
q=START;for(int i=0;i<4;i++)begin #DELAY;q+=START;
 checked:assert(q==(i+2)*START)else errs++;
 assume(q>0)else errs++;
 cover(q>START)hits++;
end
end
endmodule
module top;
wire[63:0]a,b;wire[31:0]ea,eb,ha,hb;
lane #(.BASE(3),.DELAY(2))u(a,ea,ha);lane #(.BASE(7),.DELAY(3))v(b,eb,hb);
initial begin #13;$finish;end
endmodule
