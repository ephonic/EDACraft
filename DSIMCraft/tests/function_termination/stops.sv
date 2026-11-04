module top;
 int state=0;
 function automatic void pause();state=3;$display("TRACE function before");$stop;state=4;$display("TRACE function after");endfunction
 initial begin state=1;$display("TRACE process before");$stop;state=2;$display("TRACE process after");pause();$display("TRACE caller %0d",state);$finish;end
 final $display("TRACE final %0d",state);
 endmodule
