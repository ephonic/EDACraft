package p;
 parameter integer W=7;typedef logic[W-1:0] Default;
 class C#(type T=Default,parameter integer N=W);
 T value;logic[N-1:0] lane;
 function new(T n);value=n;lane='1;endfunction
 function T get();return value;endfunction
 function int width_n();return $bits(lane);endfunction
 endclass
endpackage
module top;
 typedef logic[95:0] Default;parameter W=95;
 typedef p::C#() Original;typedef p::C#(Default,W+1) Wide;
 Original a;Wide b;int observed;logic[95:0] wide;
 initial begin a=new('1);b=new('1);observed=a.width_n();wide=b.get();$display("TRACE package %0d %h %h %0d",observed,a.get(),wide,b.width_n());end
endmodule
