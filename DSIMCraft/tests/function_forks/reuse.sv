module top;
 int total=0,hits=0,stage=0;
 function automatic void launch(input int value);
  fork begin #1;total+=value;hits++;end join_none
 endfunction
 initial begin
  for(int i=0;i<24;i++)begin launch(i);launch(i+1);wait fork;end
  stage++;#1;$display("TRACE reuse %0d %0d",hits,total);$finish;
 end
endmodule
