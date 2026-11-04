module top;
 class Base#(type T=int,parameter int W=4);
 T value;logic[W-1:0] lane;
 function new(T n);value=n;lane='1;endfunction
 virtual function T get();return value;endfunction
 function int width_n();return $bits(lane);endfunction
 endclass
 class Child#(type T=int,parameter int W=9) extends Base#(T,W);
 function new(T n);super.new(n);endfunction
 virtual function T get();return value+1;endfunction
 endclass
 typedef Base#(bit[7:0],9) B;
 typedef Child#(.W(9),.T(bit[7:0])) C;
 B b;C c;int observed,width_n;
 initial begin c=new(255);b=c;observed=b.get();width_n=b.width_n();$display("TRACE inheritance %0d %0d",b.get(),b.width_n());end
endmodule
