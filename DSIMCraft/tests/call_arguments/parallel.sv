`timescale 1ns/1ps
module lane #(parameter STEP=2,parameter BASE=3)(output logic[15:0] q,output logic error);
integer state=BASE,calls=0,temp=0,i;
function integer advance(input integer x=state,output integer count=temp);
 begin state=x+3;calls++;count=calls;return state;end
endfunction
task tick(input integer x=state,output logic[15:0] value=q);
 begin #1 value=advance(.x(x));end
endtask
initial begin
 q=0;error=0;
 for(i=0;i<5;i=i+1)begin
  #(STEP) tick(.value());
  if(q!==BASE+(i+1)*3||temp!==i+1||calls!==i+1)error=1;
 end
end
endmodule
module top;
wire[15:0] a,b;wire ea,eb;
lane #(.STEP(2),.BASE(3))u(a,ea);
lane #(.STEP(3),.BASE(17))v(b,eb);
endmodule
