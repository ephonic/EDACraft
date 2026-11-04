module top;
 int state=7;int result=initialize();int skipped=later();
 function automatic int initialize();state=8;$display("TRACE startup");$finish;state=9;return 10;endfunction
 function automatic int later();$display("BAD initializer");return 33;endfunction
 initial $display("BAD initial");
 final $display("TRACE final %0d %0d %0d",state,result,skipped);
 endmodule
