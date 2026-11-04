module top;
 typedef int Q[$];Q stored;
 int observed;
 function automatic Q bump(input int n);return {n,n+1};endfunction
 initial begin stored=bump(3);observed=stored[0];#2;stored=bump(12);observed=stored[0];#2;stored=bump(5);observed=stored[0];#2;stored=bump(24);observed=stored[0];#1;$finish;end
 initial begin #1;$display("TRACE r1 %0d",stored[0]);#2;$display("TRACE r3 %0d",stored[0]);#2;$display("TRACE r5 %0d",stored[0]);end
endmodule
