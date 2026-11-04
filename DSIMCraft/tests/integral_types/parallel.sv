`timescale 1ns/1ps
module lane #(parameter BASE=3)(output time q);
function time bump(input time value);
 begin return value+64'h100000000;end
endfunction
task step(input integer unsigned n,output time value);
 begin #1;value=bump(BASE+n*3);end
endtask
initial begin:run
 time tmp;
 q=0;
 for(integer unsigned i=0;i<5;i++)begin step(i,tmp);q<=#1 tmp;end
end
endmodule
module top;
wire[63:0]a,b;
lane #(3)u(a);lane #(17)v(b);
initial begin #8;$finish;end
endmodule
