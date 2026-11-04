module top;
 class Payload;int value;endclass
 class Lookup #(type T=int);
  typedef T map_t[string];
  static function bit check(ref map_t entries,input string name);return entries.exists(name);endfunction
 endclass
 class Store;Payload values[string];endclass
 Store store;Payload payload;int seen;
 initial begin store=new();payload=new();store.values["found"]=payload;seen=Lookup#(Payload)::check(store.values,"found");$display("TRACE checker %0d %0d",seen,Lookup#(Payload)::check(store.values,"missing"));end
 endmodule
