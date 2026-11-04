module top;
 typedef int queue_t[$];
 class Store;queue_t rows[string];endclass
 Store store;int seen;
 function automatic void edit(ref queue_t items[string]);items["row"].push_back(43);items["row"].push_back(5);endfunction
 initial begin store=new();edit(store.rows);seen=store.rows["row"].pop_front();$display("TRACE queues %0d %0d %0d",seen,store.rows.num(),store.rows["row"][0]);end
 endmodule
