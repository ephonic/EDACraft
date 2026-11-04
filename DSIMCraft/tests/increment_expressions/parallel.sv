`timescale 1ns/1ps
module lane #(parameter BASE=3)(output reg[31:0]q=0);
function integer calc(input integer n);
 begin return BASE+3*n++;end
endfunction
task step(input integer n,output integer result);
 begin #1;result=calc(n++);return;end
endtask
initial begin:run
 integer i=0,temp;
 while(i<5)begin step(i++,temp);q<=#1 temp;end
end
endmodule
module top;
wire[31:0]a,b;
lane #(3)u(a);lane #(17)v(b);
endmodule
