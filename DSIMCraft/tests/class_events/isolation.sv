`timescale 1ps/1ps
module top;
 class Base;
  event pulse;
  function void fire();->pulse;endfunction
 endclass
 class Derived extends Base;
  event extra;
  task fire_extra();->extra;endtask
 endclass
 Derived a,b;Base alias_a;int first=0,second=0,extra=0;
 initial begin
  a=new;b=new;alias_a=a;
  fork
   begin @(alias_a.pulse);first++;@(a.extra);extra++;end
   begin @(b.pulse);second++;end
   begin #1;a.fire();#1;
    if(first!=1||second!=0||extra!=0)$fatal(1,"instance isolation");
    a.fire_extra();#1;b.fire();
   end
  join
  if(first!=1||second!=1||extra!=1)$fatal(1,"inherited event identity");
  $display("TRACE class isolation %0d %0d %0d",first,second,extra);$finish;
 end
endmodule
