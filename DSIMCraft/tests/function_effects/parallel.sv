`timescale 1ns/1ps
module lane #(parameter STEP=2,parameter BASE=3)(output logic[15:0] q,output logic error);
integer state=BASE,calls=0,temp=0,i;
function integer advance(input integer x,output integer count);
 begin state+=x;calls++;count=calls;return state;end
endfunction
function void tick(input integer x);
 begin q=advance(x,temp);end
endfunction
initial begin
 q=0;error=0;
 for(i=0;i<5;i=i+1)begin
  #(STEP) tick(3);
  if(q!==BASE+(i+1)*3||temp!==i+1||calls!==i+1)error=1;
 end
end
endmodule
module top;
wire[15:0] a,b;wire ea,eb;
lane #(.STEP(3),.BASE(3))u(a,ea);
lane #(.STEP(4),.BASE(17))v(b,eb);
endmodule
