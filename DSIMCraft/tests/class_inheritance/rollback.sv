`timescale 1ps/1ps
module top;
class Base;
 int n;
 virtual function int get();return n;endfunction
endclass
class Derived extends Base;
 int extra;
 function new(int v);n=v;extra=v+1;endfunction
 function int get();return n+extra;endfunction
endclass
Base p;Derived d,e;int observed;
initial begin
 d=new(3);p=d;
 #2;d.extra=10;e=new(5);p=e;
 #2;observed=p.get();
 #2;$display("TRACE rollback t=%0t value=%0d old=%0d equal=%0d",$time,observed,d.get(),p==e);$finish;
end
initial begin #1;wait(p.n==5);observed=p.get();end
endmodule
