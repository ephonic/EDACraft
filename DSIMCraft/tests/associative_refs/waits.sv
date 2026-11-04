module top;
 class Store;int values[string];endclass
 Store store;int seen;
 task automatic observe(ref int items[string]);wait(items.exists("go"));seen=items["go"];$display("TRACE wait %0d",seen);endtask
 task automatic publish(ref int items[string]);#2;items["go"]=17;endtask
 initial begin store=new();fork observe(store.values);publish(store.values);join $display("TRACE done %0d %0d",seen,store.values.num());end
 endmodule
