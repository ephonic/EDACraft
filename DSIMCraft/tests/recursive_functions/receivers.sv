`timescale 1ps/1ps
module top;
 class Node;
  int weight;
  Node link;
  function int sum(int n);
   int saved;
   saved=weight;
   if(n==0||link==null)return saved;
   return saved+link.sum(n-1)+weight;
  endfunction
 endclass
 Node a,b;
 int calls,observed;
 function automatic Node choose();calls++;return a;endfunction
 function automatic int depth();calls++;return 3;endfunction
 initial begin
  a=new;b=new;a.weight=2;b.weight=5;a.link=b;b.link=a;
  observed=choose().sum(depth());
  if(observed!=23||calls!=2||a.weight!=2||b.weight!=5)$fatal(1,"receiver activation");
  #2 $display("TRACE recursive receivers %0d %0d",observed,calls);$finish;
 end
endmodule
