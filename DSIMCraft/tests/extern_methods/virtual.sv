module top;
 class Base;
  local int value;
  extern function new(int x=3);
  extern protected function int hidden();
  extern virtual function int get(int x=1);
 endclass
 class Derived extends Base;
  extern function new(int x=5);
  extern virtual function int get(int x=1);
 endclass
 function Base::new(int x);value=x;endfunction
 function int Base::hidden();return value;endfunction
 function int Base::get(int x);return hidden()+x;endfunction
 function Derived::new(int x);super.new(x);endfunction
 function int Derived::get(int x);return super.get(x)*2;endfunction
 Base handle;Derived child;int observed;
 initial begin
  child=new(7);handle=child;observed=handle.get();$display("TRACE virtual %0d",observed);
  #1;observed=handle.get(3);$display("TRACE later %0d",observed);$finish;
 end
endmodule
