`timescale 1ps/1ps
module top;
 virtual class Base;
  int n;
  pure virtual function int get();
  pure virtual task bump(int amount=2);
 endclass
 class Derived extends Base;
  int k;
  function new(int value);n=value;k=value+1;endfunction
  function int get();return n+k;endfunction
  task bump(int amount=3);#1;k=k+amount;endtask
 endclass
 Base b;Derived d,selected;int observed,ok,phase;
 initial begin
  d=new(3);b=d;ok=$cast(selected,b);observed=selected.get();
  #2;d=new(5);b=d;ok=$cast(selected,b);phase=1;
  b.bump();observed=selected.get();phase=2;
  #3;$display("TRACE rollback %0d %0d %0d %0d %0d",observed,ok,phase,selected==d,selected.k);$finish;
 end
 initial begin #1;wait(selected.n==5);observed=selected.get();end
endmodule
