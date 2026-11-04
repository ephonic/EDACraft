module top;
 int total=0,stage=0;
 function automatic void leaf(input int value);
  fork begin #1;total+=value;end join_none
 endfunction
 function automatic void launch(input int value);
  fork begin
   leaf(value);wait fork;
   fork begin #1;total+=100;end join
  end join_none
 endfunction
 initial begin launch(3);launch(5);wait fork;stage++;#1;$display("TRACE nested %0d",total);$finish;end
endmodule
