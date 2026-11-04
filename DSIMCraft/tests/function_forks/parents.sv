module top;
 int total=0,stage=0;
 function automatic void launch(input int value);
  fork begin #3;total+=value;end join_none
 endfunction
 initial begin launch(1);#1;disable fork;#4;$display("TRACE cancelled %0d",total);stage++;#1;$finish;end
 initial begin launch(10);wait fork;$display("TRACE sibling %0d",total);end
endmodule
