`timescale 1ps/1ps
module top;
 typedef class Item;
 virtual class Base;int n;pure virtual function int get();endclass
 class Item extends Base;
  function new(int v=0);n=v;endfunction
  function int get();return n;endfunction
 endclass
 typedef enum {EMPTY=0,READY=1,DONE=2} State;
 Base q[$],a[int],selected;Item item=new(3);State states[$],phase;
 int observed;
 initial begin
  q.push_back(item);a[-1]=item;states.push_back(READY);observed=q[0].get();
  #2;item=new(5);q.push_front(item);a[-1]=q.pop_front();selected=a[-1];phase=states.pop_front();observed=selected.get();
  #1;a[-1].n=7;states.push_back(DONE);observed=selected.get();
  #2;$display("TRACE rollback %0d %0d %0d",observed,q.size(),states.pop_back());$finish;
 end
endmodule
