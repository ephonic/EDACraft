module top;
 class Box#(type T=int);
  T value;function new(T n);value=n;endfunction
  static function int tag();return 17;endfunction
 endclass
 function logic[64:0] sum(int prefix,Box#(int) x,Box#(logic[64:0]) y);
  return prefix+x.value+y.value;
 endfunction
 Box#(int) a;Box#(logic[64:0]) b;logic[64:0] observed;
 initial begin
  a=new(3);b=new(65'h10000000000000000);observed=sum(2,a,b);
  $display("TRACE basic %h %0d",observed,Box#(int)::tag());
 end
endmodule
