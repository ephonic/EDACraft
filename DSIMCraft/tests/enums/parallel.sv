`timescale 1ns/1ps
module lane #(parameter int BASE=3,parameter int D=2)(output logic [63:0] q,output logic error);
typedef enum byte {FIRST,SECOND,THIRD,FOURTH,FIFTH,LIMIT} count_t;
count_t count;
initial begin
 error=0;
 for(count=FIRST;count<LIMIT;count++) begin
  q=64'(BASE*(count+1));
  if(q!==64'(BASE*(count+1)))error=1;
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
