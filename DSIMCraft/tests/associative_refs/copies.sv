module top;
 class Store;int values[string];endclass
 Store store;int source[string];int seen;
 function automatic void replace(ref int destination[string],const ref int origin[string]);destination=origin;endfunction
 initial begin store=new();source["a"]=47;store.values["old"]=2;replace(store.values,source);source["a"]=9;seen=store.values["a"];$display("TRACE copy %0d %0d %0d",seen,store.values.num(),store.values.exists("old"));end
 endmodule
