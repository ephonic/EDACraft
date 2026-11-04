module top;
 int first=10,second=20,total=0,stage=0;
 function automatic void launch(ref int value,input int delta,const ref int observed);
  fork begin #1;value+=delta;total+=observed;end join_none
 endfunction
 initial begin
  launch(first,2,second);launch(second,4,first);wait fork;
  stage++;#1;$display("TRACE references %0d %0d %0d",first,second,total);$finish;
 end
endmodule
