module top;
 class Base #(type T=int, U=T, int N=3, M=N+1);
  T value;U other;
  extern function new(T v,U w);
  extern virtual function Base::T get();
 endclass
 function Base::new(T v,U w);value=v;other=w;endfunction
 function Base::T Base::get();return value+other+M;endfunction
 class Derived #(type T=int, U=T, int N=4, M=N+2) extends Base#(T,U,N,M);
  function new(T v,U w);super.new(v,w);endfunction
  function T get();return super.get()+N;endfunction
 endclass
 Derived#(logic[64:0],logic[64:0],7) a;
 Base#(logic[64:0],logic[64:0],7,9) base;
 logic[64:0] observed;
 initial begin a=new(65'h10000000000000000,2);base=a;observed=base.get();$display("TRACE inherited %h",observed);end
endmodule
