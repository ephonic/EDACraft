package p;
 class Shared;
  static int x=5;
  static function int add();x++;return x;endfunction
 endclass
endpackage
module leaf(output int observed);
 class C;
  static int x=10;
  static function int add();x++;return x;endfunction
 endclass
 int own,shared;
 initial begin own=C::add();shared=p::Shared::add();#1;observed=C::x;end
endmodule
module top;
 wire [31:0] a,b;
 leaf u(a),v(b);
 initial begin #2;$display("TRACE clone %0d %0d %0d",a,b,p::Shared::x);$finish;end
endmodule
