`timescale 1ps/1ps
module top;
 typedef class Derived;
 virtual class Base;
  Derived peer;
  pure virtual function int get();
  pure virtual task bump();
 endclass
 class Derived extends Base;
  int n;
  function new(int value);n=value;endfunction
  function int get();return n;endfunction
  task bump();#1;n+=2;endtask
 endclass
 Derived d=new(3),selected;Base b;int observed,ok;
 initial begin
  b=d;ok=$cast(selected,b);b.peer=selected;observed=b.get();
  #2;d=new(5);d.peer=d;b=d;b.bump();observed=b.get();
  #3;$display("TRACE rollback %0d %0d %0d",observed,ok,b.peer==d);$finish;
 end
 initial begin #1;wait(b.peer.n==5);observed=b.peer.get();end
endmodule
