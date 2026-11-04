module top;
 int observed=0,calls=0,source=10;
 function automatic int next_value();calls++;return calls+4;endfunction : next_value
 task automatic step(input bit[3:0] a,input int b=a+2,input int c=b+3);
  #1;observed=c;
 endtask : step
 function automatic int ref_read(const ref int a,input int b=a+1);return b;endfunction : ref_read
 task automatic ref_step(ref int a,input int b=a+2);#1;a=b;observed=b;endtask : ref_step
 initial begin
  step(next_value());
  if(observed!=10||calls!=1)$fatal(1,"task default repeated actual");
  $display("TRACE defaults task %0d %0d",observed,calls);
  step(31);$display("TRACE defaults task converted %0d",observed);
  $display("TRACE defaults ref read %0d",ref_read(source));
  ref_step(source);$display("TRACE defaults ref task %0d %0d",source,observed);
  #1;$finish;
 end
endmodule
