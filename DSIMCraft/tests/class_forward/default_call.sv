`timescale 1ps/1ps
package p;
 int seed=19;
 typedef class Reporter;
 function automatic int invoke();
  Reporter r;
  r=new;
  return r.value();
 endfunction
 function automatic int read(int offset=3, int value=invoke()+offset);
  return value;
 endfunction
 class Client;
  static function int read(int value=invoke());return value+5;endfunction
  task change(output int target, input int value=invoke());#1;target=value+7;endtask
 endclass
 typedef class Handler;
 class Reporter;
  Handler h;
  function int value();h=new;return h.n;endfunction
 endclass
 class Handler;int n=seed;endclass
endpackage
module top;
 p::Client c;
 int first,second,third,overridden;
 initial begin
  c=new;first=p::read();p::seed=23;second=p::Client::read();
  c.change(third);overridden=p::read(5,31);
  #1;$display("TRACE defaults %0d %0d %0d %0d",first,second,third,overridden);
 end
endmodule
