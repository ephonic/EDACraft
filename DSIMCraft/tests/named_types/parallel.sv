`timescale 1ns/1ps
module lane #(parameter int BASE=3,parameter int D=2)(output logic [63:0] q,output logic error);
typedef byte count_t;
typedef logic [63:0] output_t;
count_t count;
initial begin: run
 error=0;
 for(count=0;count<5;count++) begin
  q=output_t'(BASE*(count+1));
  if(q!==64'(BASE*(count+1))) error=1;
  #D;
 end
end
endmodule
module top;
wire [63:0] a,b;
wire ea,eb;
lane #(.BASE(3),.D(2))u(a,ea);
lane #(.BASE(7),.D(3))v(b,eb);
initial #16 $finish;
endmodule
