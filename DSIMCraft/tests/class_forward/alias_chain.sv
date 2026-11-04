`timescale 1ps/1ps
module top;
 typedef class A;typedef class B;typedef A Early;
 class Client;
  A value;B other;
  function Early pass(B x);return x;endfunction
  task change(ref Early x,input A y);x=y;endtask
 endclass
 typedef B A;
 class Impl;int value=31;endclass
 typedef Impl B;
 typedef class A;
 Client c;Early a=new;Impl b;int observed;
 initial begin c=new;c.value=a;b=c.pass(a);c.change(a,b);observed=a.value;
  #1;$display("TRACE chain %0d %0d",observed,c.value==b);end
endmodule
