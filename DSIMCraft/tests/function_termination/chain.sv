module top;
 int side=0,value=9;
 function automatic int die(ref int target);target=3;$display("TRACE inner %0d",target);$finish(0);target=4;return 5;endfunction
 function automatic int outer();$display("TRACE outer");return die(side);endfunction
 initial begin #2;value=outer();side=99;$display("BAD after");end
 final $display("TRACE final %0d %0d",side,value);
 endmodule
