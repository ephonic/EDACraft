module top;
 class C;function new();$display("TRACE constructor");$finish;$display("BAD constructor");endfunction endclass
 C item;
 initial begin #1;item=new();$display("BAD constructed");end
 final $display("TRACE final %0d",item==null);
 endmodule
