module top;
 int total=0;
 function automatic int launch(input int value);
  fork begin #1;total+=value;end join_none
  return value+1;
 endfunction
 int a=launch(4),b=launch(9);
 initial begin #2;$display("TRACE startup %0d %0d %0d",a,b,total);$finish;end
endmodule
