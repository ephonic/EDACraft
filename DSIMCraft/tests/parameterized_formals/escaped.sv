module top;
 parameter \odd)name =9;
 class Box#(int W=1);logic[W-1:0] value;function new();value='1;endfunction endclass
 function int width_n(int n,Box#(\odd)name ) obj,Box#($bits("ignore ) /* */ # (")) text_obj);
  return n+$bits(obj.value)+$bits(text_obj.value);
 endfunction
 Box#(9) a;Box#($bits("ignore ) /* */ # (")) b;int observed;
 initial begin a=new;b=new;observed=width_n(1,a,b);$display("TRACE escaped %0d",observed);end
endmodule
