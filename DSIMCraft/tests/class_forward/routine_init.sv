`timescale 1ps/1ps
module top;
 typedef class Reporter;
 function automatic int invoke();
  Reporter r;
  r=new;
  return r.value();
 endfunction
 function automatic int read(input int x);
  int n=invoke(),m=n+x;
  return m;
 endfunction
 task automatic read_task(output int out);
  int n=invoke();
  #1;out=n+5;
 endtask
 function automatic int legacy;
  input int x;
  int n=invoke();
  legacy=n+x;
 endfunction
 typedef class Handler;
 class Reporter;
  Handler h;
  function int value();h=new;return h.n;endfunction
 endclass
 class Handler;int n=19;endclass
 int observed,second,third;
 initial begin
  observed=read(4);read_task(second);third=legacy(6);
  #1;$display("TRACE routine %0d %0d %0d",observed,second,third);
 end
endmodule
