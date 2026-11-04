module top;
 typedef int Q[$];
 int calls;
 function automatic Q build(input int n);calls++;return {n,n+1};endfunction
 Q global_values=build(3);
 task automatic work(input int n);
  Q local_values=build(n);
  static Q saved=build(20);
  local_values={local_values,build(n+10),99};
  $display("TRACE init %0d %0d %0d %0d %0d",local_values.size(),local_values[2],saved[0],global_values[0],calls);
 endtask
 initial begin #1;work(5);#1;work(8);#1;$finish;end
endmodule
