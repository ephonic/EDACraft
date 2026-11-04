module top;
 class Key;endclass
 class Store;
  string values[Key];
  task automatic put(Key key,string value);#1;values[key]=value;endtask
  function string get(Key key);return values[key];endfunction
  function int count();return values.num();endfunction
 endclass
 Store a,b;Key k;int total;
 initial begin
  a=new;b=new;k=new;
  fork a.put(k,"left");b.put(k,"right");join
  if(a.get(k)!="left"||b.get(k)!="right"||a.count()!=1)$fatal(1,"concurrent methods");
  a.put(k,"again");if(a.get(k)!="again"||b.get(k)!="right")$fatal(1,"frame reuse");
  $display("TRACE class string tasks %s %s",a.get(k),b.get(k));$finish;
 end
endmodule
