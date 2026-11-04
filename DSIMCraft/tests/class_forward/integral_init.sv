`timescale 1ps/1ps
package p;
 typedef class Reporter;
 function automatic int invoke();
  Reporter r;
  r=new;
  return r.value();
 endfunction
 // Integral result: its call must wait for the later forward declaration.
 int observed=invoke();
 typedef class Handler;
 class Reporter;
  Handler h;
  function int value();h=new;return h.n;endfunction
 endclass
 class Handler;int n=19;endclass
endpackage
module top;
 initial begin #1;$display("TRACE startup %0d",p::observed);end
endmodule
