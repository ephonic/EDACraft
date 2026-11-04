`timescale 1ps/1ps
module top;
class Leaf;
 int value;
 function new(int n);value=n;endfunction
 function int get();return value;endfunction
endclass
class Branch;
 Leaf child;
 function new(int n);child=new(n);endfunction
 function int get();return child.get()+1;endfunction
endclass
Branch p,q;int observed;
initial begin
 p=new(8);q=p;
 observed=q.get();
 $display("TRACE nested value=%0d",q.get());
 q.child.value=20;
 observed=p.get();
 $display("TRACE child alias=%0d",p.get());
 $finish;
end
endmodule
