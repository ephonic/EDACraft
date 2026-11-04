`timescale 1ps/1ps
module top;
 class Item;int n;function new(int v=0);n=v;endfunction endclass
 typedef enum {ZERO=0,TWO=2,THREE=3} State;
 int observed;
 function automatic int calc(input int n);
  Item q[$],a[int],v;State e[$];
  v=new(n);q.push_back(v);a[-n]=q.pop_back();e.push_back(TWO);
  return a[-n].n+int'(e.pop_front());
 endfunction
 task automatic collect(input int n);
  Item q[$],v;State states[$];
  v=new(n);q.push_back(v);states.push_back(THREE);
  #2;v=q.pop_front();observed+=v.n+int'(states.pop_front());
 endtask
 initial begin
  observed=calc(2)+calc(4);
  fork collect(3);begin #1;collect(5);end join
  $display("TRACE lifetime %0d",observed);
 end
endmodule
