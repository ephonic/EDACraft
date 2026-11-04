module top;
 typedef bit[64:0] key_t;typedef bit signed[7:0] signed_t;
 class Store;int wide[key_t];int narrow[signed_t];endclass
 Store store;int seen;
 function automatic void wide_edit(ref int items[key_t]);items[65'h10000000000000001]=31;endfunction
 function automatic void narrow_edit(ref int items[signed_t]);items[-5]=7;endfunction
 initial begin store=new();wide_edit(store.wide);narrow_edit(store.narrow);seen=store.wide[65'h10000000000000001]+store.narrow[-5];$display("TRACE typed %0d %0d %0d",seen,store.wide.num(),store.narrow.num());end
 endmodule
