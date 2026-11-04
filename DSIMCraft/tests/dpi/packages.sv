package functions;
 import "DPI-C" pure function int add_one(input int x);
 import "DPI-C" context function int context_scope();
 import "DPI-C" function int ordinary_scope();
 export "DPI-C" pkg_hook = function hook;
 function automatic int hook(input int x);return x+3;endfunction
endpackage
module top;
 import functions::*;
 int observed;
 initial begin
  observed=add_one(8);
  $display("TRACE package %0d %0d %0d",observed,context_scope(),ordinary_scope());
  #1;observed=add_one(observed);$display("TRACE later %0d",observed);$finish;
 end
endmodule
