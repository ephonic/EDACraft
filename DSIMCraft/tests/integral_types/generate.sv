`timescale 1ns/1ps
module worker #(parameter N=2)(output time q);
time counter=64'h100000000;
function time calc(input integer unsigned n);
 begin return counter+n;end
endfunction
initial begin:run
 q=0;
 for(integer unsigned i=0;i<N;i++)begin #1;q<=#1 calc(i);counter++;end
end
endmodule
module top;
genvar g;
for(g=0;g<2;g=g+1)begin:lanes
 wire[63:0]q;
 worker #(g+2)u(q);
end
initial begin #6;$finish;end
endmodule
