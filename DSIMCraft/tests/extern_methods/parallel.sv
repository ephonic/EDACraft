module lane #(parameter int N=1)(output int observed);
 class Math;
  extern static function int twice(input int x);
 endclass
 function int Math::twice(input int x);return x*2;endfunction
 initial begin observed=N;#1;observed=Math::twice(observed);#2;observed=Math::twice(observed+1);end
endmodule
module top;wire[31:0] a,b;lane #(1) u(a);lane #(4) v(b);initial #5 $finish;endmodule
