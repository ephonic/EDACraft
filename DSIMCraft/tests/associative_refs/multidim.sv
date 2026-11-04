module top;
 class Store;int grid[string][int];endclass
 Store store;int seen;
 function automatic void edit(ref int items[string][int]);items["row"][-2]=41;items["row"][5]=3;endfunction
 function automatic int count(const ref int items[string][int]);int total;total=0;foreach(items[r,c])total+=items[r][c];return total;endfunction
 initial begin store=new();edit(store.grid);seen=count(store.grid);$display("TRACE multidim %0d %0d %0d",seen,store.grid.num(),store.grid["row"].num());end
 endmodule
