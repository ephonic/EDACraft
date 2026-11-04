module top;
 class Box #(type T=int, int W=8);
  const T value;
  static const int width=W;
  const static int offset=W+1;
  extern function new(T n);
  function T get();return value;endfunction
 endclass
 function Box::new(T n);value=n;endfunction
 Box#(int,8) a;
 Box#(logic[70:0],71) b;
 int observed;
 initial begin
  a=new(-7);b=new(71'h12_3456789abcdef012);
  if(a.get()!=-7 || b.get()!=71'h12_3456789abcdef012 || a.width!=8 || b.width!=71 || a.offset!=9 || b.offset!=72)$fatal(1,"specialization const metadata");
  observed=a.width+b.width;#1;$display("TRACE const generic widths=%0d",observed);$finish;
 end
endmodule
