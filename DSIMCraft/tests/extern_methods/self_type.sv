module top;
 class C #(type T=int);
  T value;
  extern function new(T n);
  extern function C#(T) self();
  extern function T get();
 endclass
 function C::new(T n);value=n;endfunction
 function C#(C::T) C::self();return this;endfunction
 function C::T C::get();return value;endfunction
 C#(byte) one,one_copy;C#(longint) two,two_copy;longint observed;
 initial begin
  one=new(-7);two=new(64'sd5000000000);one_copy=one.self();two_copy=two.self();
  observed=one_copy.get()+two_copy.get();
  $display("TRACE self %0d %0d %0d %0d",one_copy.get(),two_copy.get(),one_copy==one,two_copy==two);
  #1;one_copy.value=8;observed=one.get()+two_copy.get();$display("TRACE alias %0d",observed);$finish;
 end
endmodule
