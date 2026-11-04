module top;
 class Secret;
  local int value;
  local function new(int n);value=n;endfunction
  static function Secret create(int n);Secret h;h=new(n);return h;endfunction
  function int get();return value;endfunction
 endclass
 class B;
  protected int value;
  protected function new(int n=9);value=n;endfunction
  function int get();return value;endfunction
 endclass
 class D extends B;
  function new(int n);super.new(n);endfunction
 endclass
 class E extends B;endclass
 Secret h;D d;E e;int observed;
 initial begin h=Secret::create(12);d=new(21);e=new;observed=h.get()+d.get()+e.get();$display("TRACE constructors %0d",observed);#1;$finish;end
endmodule
