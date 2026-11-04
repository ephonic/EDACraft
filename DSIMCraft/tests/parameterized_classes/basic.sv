module top;
 class Box #(type T=int, parameter int W=8);
  T v;logic[W-1:0] lane;
  function new(T n);v=n;lane='1;endfunction
  function T get();return v;endfunction
  function int width_n();return $bits(lane);endfunction
 endclass
 typedef Box#(logic[64:0],65) Wide;
 typedef Box#(.W(65),.T(logic[64:0])) Other;
 Wide a,b;Other c;Box#(int,4) d;Box normal;Box#() explicit_default;Box#(.T(),.W()) named_default;
 logic[64:0] observed;int widths;
 initial begin
  a=new(65'h1fedcba9876543210);b=a;c=b;d=new(9);normal=new(17);explicit_default=normal;named_default=explicit_default;
  observed=c.get();widths=c.width_n()+d.width_n();
  $display("TRACE basic %h %0d %0d %0d %0d",c.get(),c.width_n(),d.width_n(),d.get(),explicit_default.get());
 end
endmodule
