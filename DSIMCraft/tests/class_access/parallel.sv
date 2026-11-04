module leaf #(parameter int V=1)(output int observed);
 class C;
  local static int x=0;
  static task work();#1;x=V;#2;x++;endtask
  static function int get();return x;endfunction
 endclass
 initial begin C::work();observed=C::get();end
endmodule
module top;
 wire [31:0] a,b;
 leaf #(7) u(a);leaf #(19) v(b);
endmodule
