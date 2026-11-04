module top;
 int direct=1,copied=9;
 function automatic int die(ref int a,output int b);a=4;b=7;$display("TRACE function");$finish;return 1;endfunction
 task automatic run();int unused;unused=die(direct,copied);$display("BAD task");endtask
 initial begin #1;run();$display("BAD initial");end
 final $display("TRACE final %0d %0d",direct,copied);
 endmodule
