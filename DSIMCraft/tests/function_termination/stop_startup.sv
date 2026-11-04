module top;
 int state=0;int result=pause();int after=later();
 function automatic int pause();state++;$display("TRACE startup before");$stop;state++;$display("TRACE startup after");return 3;endfunction
 function automatic int later();$display("TRACE later");return 7;endfunction
 initial begin $display("TRACE initial %0d %0d %0d",state,result,after);$finish;end
 final $display("TRACE final %0d",state);
 endmodule
