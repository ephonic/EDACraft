`timescale 1ns/1ps
module child #(parameter int N=3)(output int errs,output int hits,output reg[31:0]q);
function int f(input int a);
begin
 check_arg:assert(a>=0)f=a+1;else f=0;
end
endfunction
task check(input int a);
begin assume(a==N)hits++;else errs++;cover(a>0)hits++;end
endtask
genvar g;generate for(g=0;g<2;g=g+1)begin:lane
 initial begin #1;local_check:assert(N>g)else errs++;end
end endgenerate
initial begin
 errs=0;hits=0;q=f(N);check(N);check(N+1);#2;
 assert(q==N+1)hits++;else errs++;
 q<=f(-1);#1;assert(q==0)hits++;else errs++;
end
endmodule
module top;
wire[31:0]a,b,ea,eb,ha,hb;
child u(ea,ha,a);child #(.N(1))v(eb,hb,b);
initial begin #4;$display("TRACE hierarchy %0d %0d %0d %0d %0d %0d",a,b,ea,eb,ha,hb);$finish;end
endmodule
