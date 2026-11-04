`timescale 1ns/1ps
module lane #(parameter BASE=3)(output reg [31:0] q=0);
function integer calc(input integer a);
 begin calc=a*3+BASE;end
endfunction
task step(input integer a,output [31:0] b);
 begin #1;b=calc(a);end
endtask
initial begin : run
 integer temp;
 for(int i=0;i<5;i++)begin
  step(i,temp);q<=#1 temp;
 end
end
endmodule
module top;
wire [31:0] a,b;
lane #(3) u(a);lane #(17) v(b);
endmodule
