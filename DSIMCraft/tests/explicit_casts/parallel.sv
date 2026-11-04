`timescale 1ns/1ps
module lane #(parameter int BASE=3,D=2)(output logic [63:0] q,output int errors);
initial begin:run
 q=0;errors=0;
 for(int i=0;i<5;i++)begin
 q=64'(byte'(BASE*(i+1)));
 assert(q==BASE*(i+1))else errors++;
 #D;
 end
end
endmodule
module top;
wire [63:0] a,b;wire [31:0] ea,eb;
lane #(.BASE(3),.D(2))u(a,ea);
lane #(.BASE(7),.D(3))v(b,eb);
initial #13 $finish;
endmodule
