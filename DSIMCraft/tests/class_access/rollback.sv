module top;
 class C;
  local static int x=3;
  protected static function void put(int v);x=v;endfunction
  static function int get();return x;endfunction
  static function void update(int n);put(n);endfunction
 endclass
 int observed;
 initial begin observed=C::get();#2;C::update(12);observed=C::get();#2;C::update(5);observed=C::get();#2;C::update(24);observed=C::get();#1;$finish;end
 initial begin #1;$display("TRACE r1 %0d",C::get());#2;$display("TRACE r3 %0d",C::get());#2;$display("TRACE r5 %0d",C::get());end
endmodule
