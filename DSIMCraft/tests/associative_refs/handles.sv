module top;
 class Key;int tag;endclass
 class Payload;int value;endclass
 class Store;Payload entries[Key];endclass
 Store store;Key key;Payload payload;int seen;
 function automatic void edit(ref Payload items[Key],input Key k,input Payload p);items[k]=p;items[k].value=37;endfunction
 initial begin store=new();key=new();payload=new();edit(store.entries,key,payload);seen=payload.value;$display("TRACE handles %0d %0d %0d",seen,store.entries.num(),store.entries.exists(key));end
 endmodule
