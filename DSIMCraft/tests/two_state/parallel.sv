`timescale 1ns/1ps
module lane #(parameter BASE=3)(input int seed,output longint q);
initial begin:run
q=0;for(int i=0;i<5;i++)begin #2;q=seed+BASE+i;end
end
endmodule
module top;
reg[31:0]a=32'hx0000010,b=32'hz0000020;wire signed[63:0]x,y;
lane #(3)u(a,x);lane #(7)v(b,y);
initial begin #11;$finish;end
endmodule
