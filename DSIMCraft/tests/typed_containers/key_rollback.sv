`timescale 1ps/1ps
module top;
 class Key;int id;function new(int n);id=n;endfunction endclass
 class Store;int values[Key];endclass
 Key a,b,k;Store store;int values[Key],saved[Key];int observed;
 initial begin
  a=new(1);b=new(2);store=new;values[a]=3;store.values[b]=4;saved=values;observed=7;
  #2;values.delete(a);values[b]=9;store.values[a]=6;store.values.delete(b);observed=values[b]+store.values[a];
  #1;a.id=5;values[null]=2;observed=values[b]+store.values[a]+saved[a]+a.id;
  #2;if(values.exists(a)||!saved.exists(a)||store.values.exists(b))$fatal(1,"rollback storage");
  if(!values.first(k)||k!=null)$fatal(1,"null first");
  $display("TRACE key rollback %0d %0d %0d",observed,values.num(),store.values.num());$finish;
 end
endmodule
