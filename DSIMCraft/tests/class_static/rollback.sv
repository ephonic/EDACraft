module top;
 class C;
  static int x=3;
  static function void put(int v);x=v;endfunction
 endclass
 int observed;
 initial begin observed=C::x;#2;C::put(12);observed=C::x;#2;C::put(5);observed=C::x;#2;C::put(24);observed=C::x;#1;$finish;end
 initial begin #1;$display("TRACE r1 %0d",C::x);#2;$display("TRACE r3 %0d",C::x);#2;$display("TRACE r5 %0d",C::x);end
endmodule
