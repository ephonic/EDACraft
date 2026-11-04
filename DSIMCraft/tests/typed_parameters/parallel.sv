`timescale 1ns/1ps
module lane #(parameter int BASE=3,parameter int DELAY=2)(output longint q);
localparam longint START=BASE;
initial begin:run
localparam int COUNT=4;
q=START;for(int i=0;i<COUNT;i++)begin #DELAY;q+=START;end
end
endmodule
module top;
wire signed[63:0]a,b;lane #(.BASE(3),.DELAY(2))u(a);lane #(.BASE(7),.DELAY(3))v(b);
initial begin #13;$finish;end
endmodule
