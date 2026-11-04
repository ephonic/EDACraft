module leaf #(parameter int V=1)(output int observed);
 typedef int Q[$];Q stored;
 function automatic Q build(input int n);Q q;q.push_back(n);return q;endfunction
 initial begin #1;stored=build(V);#2;stored=build(stored[0]+1);observed=stored[0];end
endmodule
module top;
 wire[31:0] a,b;
 leaf #(7) u(a);leaf #(19) v(b);
endmodule
