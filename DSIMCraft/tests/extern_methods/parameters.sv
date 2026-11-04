module worker #(parameter int N=1);
 class Box #(type T=int,parameter int W=5);
  local T value;
  static int calls=0;
  extern function new(T x);
  extern function Box::T get(T delta=1);
  extern static function int width();
 endclass
 function Box::new(T x);value=x;endfunction
 function Box::T Box::get(Box::T delta);calls++;return value+delta;endfunction
 function int Box::width();return Box::W;endfunction
 Box #(byte,7) a;Box #(longint,13) b;int observed;
 initial begin
  a=new(-3);b=new(64'sd5000000000);
  observed=a.get();$display("TRACE param %0d %0d %0d %0d",N,observed,b.get(2),Box#(byte,7)::width());
  #1;observed=a.get(5);$display("TRACE count %0d %0d %0d %0d",N,observed,Box#(byte,7)::calls,Box#(longint,13)::calls);
 end
endmodule
module top;worker #(1) a();worker #(2) b();initial #2 $finish;endmodule
