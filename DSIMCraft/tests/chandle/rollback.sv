module top;
 import "DPI-C" pure function chandle get_handle(input int i);
 import "DPI-C" pure function int inspect_handle(input chandle p);
 import "DPI-C" function int counted_handle(input chandle p);
 import "DPI-C" function int handle_calls();
 chandle h;int observed=0;
 initial begin
  h=get_handle(0);
  #2;observed=counted_handle(h);$display("TRACE foreign %0d %0d",observed,handle_calls());
  #2;h=get_handle(1);observed=inspect_handle(h);
  #2;observed=inspect_handle(h);#2;$display("TRACE replay %0d %0d",observed,handle_calls());$finish;
 end
endmodule
