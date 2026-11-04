`timescale 1ps/1ps
module top;
int order;
function automatic int mark(int n);order=order*10+n;return order;endfunction
class Root;
 int root=mark(1);
 function new(int n=2);root=n;void'(mark(3));endfunction
endclass
class Middle extends Root;
 int middle=mark(4);
 function new(int n=5);super.new(n);void'(mark(6));endfunction
endclass
class Leaf extends Middle;
 int leaf=mark(7);
 function new(int n=8);super.new(n);void'(mark(9));endfunction
endclass
class Implicit extends Root;
 int other=mark(5);
endclass
class ViaImplicit extends Implicit;
 int last=mark(6);
 function new();super.new();endfunction
endclass
class Hidden extends Root;
 int root=9;
 function new();super.new(4);endfunction
 function int base_value();return super.root;endfunction
endclass
Leaf l;Implicit i;ViaImplicit v;Hidden h;Root r;int observed;
initial begin
 l=new(mark(2));
 $display("TRACE order=%0d root=%0d middle=%0d leaf=%0d",order,l.root,l.middle,l.leaf);
 order=0;i=new;
 $display("TRACE implicit=%0d root=%0d other=%0d",order,i.root,i.other);
 order=0;v=new;
 $display("TRACE viaimplicit=%0d root=%0d other=%0d last=%0d",order,v.root,v.other,v.last);
 h=new;r=h;observed=h.root+r.root;
 $display("TRACE hidden=%0d base=%0d receiver=%0d sum=%0d",h.root,h.base_value(),r.root,observed);
 #2;$finish;
end
endmodule
