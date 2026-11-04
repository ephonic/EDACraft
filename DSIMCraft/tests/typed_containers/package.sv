package p;
 typedef enum {OFF=0,ON=1} State;State events[$];
 class Item;int n;function new(int v=0);n=v;endfunction endclass
 typedef Item Alias;Alias items[$],a[int];
 function automatic int collect(input int n);
  Item v;v=new(n);items.push_back(v);a[-n]=items.pop_front();events.push_back(ON);
  return a[-n].n+int'(events.pop_back());
 endfunction
endpackage
module top;
 import p::*;int observed;
 initial begin observed=collect(8);$display("TRACE package %0d %0d",observed,items.size());end
endmodule
