`timescale 1ns/1ps
module lane #(parameter int BASE=3,parameter int D=2)(output logic[63:0] q,output logic error);
typedef struct packed {bit[7:0] count;bit[63:0] sum;} accumulator_t;
accumulator_t state;
initial begin
 error=0;state=0;
 for(state.count=0;state.count<5;state.count++)begin
  state.sum+=BASE;q=state.sum;
  if(q!==64'(BASE*(state.count+1)))error=1;
  #D;
 end
end
endmodule
module top;
wire[63:0] a,b;wire ea,eb;
lane #(.BASE(3),.D(2))u(a,ea);
lane #(.BASE(7),.D(3))v(b,eb);
initial #16 $finish;
endmodule
