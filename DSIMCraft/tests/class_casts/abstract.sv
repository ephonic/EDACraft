`timescale 1ps/1ps
module top;
 virtual class B;
  int n=4;
  pure virtual function int f(int x=3);
  pure virtual task run(input int x=2);
  function new(int x=4);n=x;endfunction
 endclass
 virtual class M extends B; endclass
 class D extends M;
  function int f(int y=5);return n+y;endfunction
  task run(input int y=8);#2;n=n+y;endtask
 endclass
 B b;D d;int r;
 initial begin d=new;b=d;r=b.f();$display("TRACE f %0d",r);b.run();$display("TRACE t %0d %0t",d.n,$time);#1;$finish;end
endmodule
