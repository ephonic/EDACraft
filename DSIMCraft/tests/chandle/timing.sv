module top;
 import "DPI-C" pure function chandle get_handle(input int i);
 import "DPI-C" pure function int inspect_handle(input chandle p);
 chandle h,k;int observed=0;
 initial begin
  h=get_handle(0);
  h = #1 get_handle(1);
  observed=inspect_handle(h);
  $display("TRACE delayed %0d",observed);
  k <= #1 h;
  h=null;
  #2;observed=inspect_handle(k);
  $display("TRACE nba %0d %0d",observed,h==null);
  $finish;
 end
endmodule
