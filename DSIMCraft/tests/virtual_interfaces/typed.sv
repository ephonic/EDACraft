interface bus_if;bit[15:0] data;endinterface
module top;
 typedef virtual bus_if vif_t;
 class box #(type T=int);
  T item;
  function void put(T value);item=value;endfunction
  function T get();return item;endfunction
 endclass
 bus_if a(),b();box#(virtual bus_if) storage;vif_t first,second;
 function automatic vif_t choose(input bit which,input vif_t x,input vif_t y);return which?x:y;endfunction
 initial begin
  storage=new();storage.put(a);first=storage.get();second=choose(0,first,b);
  first.data=16'h1234;second.data=16'h5678;
  if(a.data!=16'h1234||b.data!=16'h5678||first==second)$fatal(1,"type transport");
  $display("TRACE virtual typed %0h %0h",a.data,b.data);
 end
endmodule
