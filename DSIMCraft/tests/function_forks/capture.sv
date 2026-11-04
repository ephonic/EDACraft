module top;
 int total=0,children=0,stage=0;
 function automatic int start(input int value);
  int saved=value;
  fork begin #2;total+=saved;children++;end join_none
  saved++;
  return value+10;
 endfunction
 initial begin
  $display("TRACE returns %0d %0d %0d",start(2),start(7),children);
  wait fork;
  $display("TRACE children %0d %0d",children,total);stage++;#1;$finish;
 end
 initial begin #20;$fatal(1,"lost background child");end
endmodule
