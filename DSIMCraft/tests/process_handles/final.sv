`timescale 1ps/1ps
module top;
 process main_handle,last_handle;string saved;int unsigned first;int passed;
 function automatic process here();return process::self();endfunction
 initial begin main_handle=here();#1;passed=1;end
 final begin
  last_handle=here();
  if(last_handle==null||last_handle==main_handle||last_handle!=process::self())$fatal(1,"final process identity");
  last_handle.srandom(3);saved=last_handle.get_randstate();first=$urandom();
  last_handle.set_randstate(saved);if(first!=$urandom())$fatal(1,"final random state");
  $display("TRACE final %0d",passed);
 end
endmodule
