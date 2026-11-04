module unit_test #(parameter W=8)(output logic[W-1:0] observed);
 class C#(parameter int N=W,type T=logic[N-1:0]);
 T v;function new();v='1;endfunction function T get();return v;endfunction
 endclass
 C a;C#(W,logic[W-1:0]) b;
 initial begin a=new;b=a;observed=b.get();end
endmodule
module top;wire[7:0] one;wire[128:0] two;unit_test #(8)a(one);unit_test #(129)b(two);
initial begin #1;$display("TRACE clones %h %h",one,two);end endmodule
