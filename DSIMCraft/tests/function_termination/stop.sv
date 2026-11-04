module top;
 int count=0;
 function automatic void pause();count++;$display("TRACE stop before");$stop(0);count++;$display("TRACE stop after");endfunction
 initial begin #1;pause();$display("TRACE caller %0d",count);#1;$finish;end
 final $display("TRACE final %0d",count);
 endmodule
