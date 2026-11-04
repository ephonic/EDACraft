module top;
 typedef chandle H;
 import "DPI-C" pure function chandle get_handle(input int i);
 import "DPI-C" pure function int inspect_handle(input chandle p);
 import "DPI-C" function void exchange_handles(input H a, output H b, inout H c);
 import "DPI-C" context function H callback_handle(input H a, output H b, inout H c);
 export "DPI-C" function hook_handle;
 H a,b,c; int observed=0;
 function automatic H hook_handle(input H x,output H y,inout H z);
  H old;old=z;y=x;z=null;return old;
 endfunction
 initial begin
  a=get_handle(0);c=get_handle(1);
  exchange_handles(a,b,c);
  $display("TRACE exchange %0d %0d",inspect_handle(b),inspect_handle(c));
  a=callback_handle(b,b,c);
  observed=inspect_handle(a);
  $display("TRACE callback %0d %0d %0d",observed,inspect_handle(b),c==null);
  #1;$finish;
 end
endmodule
