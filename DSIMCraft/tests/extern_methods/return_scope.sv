module top;
 typedef logic[11:0] T;
 class C #(parameter int W=6);
  extern function T outer(input int x);
  typedef logic[5:0] T;
  extern function T inner(input T x);
  extern static function logic[W-1:0] packed_value();
 endclass
 // Return types precede C::method; argument types see the completed class.
 function T C::outer(input int x);return x+1;endfunction
 function C::T C::inner(input C::T x);return x^6'h3f;endfunction
 function logic[C::W-1:0] C::packed_value();return 6'h2a;endfunction
 C #() c;logic[11:0] observed;
 initial begin
  c=new;observed=c.outer(31);
  $display("TRACE scope %0d %0d %0d %0d %0d",observed,c.inner(2),C#()::packed_value(),$bits(c.outer(0)),$bits(c.inner(0)));
  #1;observed=c.outer(5000);$display("TRACE trunc %0d",observed);$finish;
 end
endmodule
