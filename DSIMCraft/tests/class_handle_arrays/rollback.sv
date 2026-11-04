`timescale 1ps/1ps
module top;
 class Item;int value;endclass
 class Store;Item items[];rand byte unsigned q[$:3];constraint c {q.size()==2;foreach(q[i])q[i] inside {[0:31]};}endclass
 Store a,b;Item x;int observed,fingerprint;
 initial begin
  a=new;b=new;x=new;x.value=1;a.items=new[2];a.items[0]=x;b.items=a.items;
  #2 if(!a.randomize())$fatal(1,"checkpoint random queue");fingerprint=a.q[0]+a.q[1]*32;a.items=new[3](a.items);a.items[1]=new;a.items[1].value=8;
  a.items[0].value=9;observed=b.items[0].value;
  if(a.items[2]!=null||a.items[1].value!=8||b.items[1]!=null)$fatal(1,"rollback references");
  #1 a.items.delete();b.items[0].value=7;observed=x.value;
  if(b.items.size()!=2||b.items[0]!=x)$fatal(1,"rollback heap identity");
  $display("TRACE class handle dynamic checkpoint heap identity pass");$finish;
 end
endmodule
