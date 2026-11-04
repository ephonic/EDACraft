package p;
 class Base;static int count=2;int a=-3;protected int hidden=7;endclass
 class Leaf #(int N=5);int value=N;endclass
 class Derived extends Base;int a=11;Leaf#(5) leaf;endclass
 class Node;int value=1;Node next;endclass
endpackage
module top;
 p::Base base;p::Derived derived;p::Leaf#(5) leaf;p::Node node;string s;int stage=0;
 initial begin
  derived=new();base=derived;$swrite(s,base);$display("TRACE dynamic <%s>",s);
  leaf=new();derived.leaf=leaf;$swrite(s,derived);$display("TRACE reference <%s>",s);
  stage++;#1;node=new();node.next=node;$swrite(s,node);$display("TRACE cycle <%s>",s);$finish;
 end
endmodule
