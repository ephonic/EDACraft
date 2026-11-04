module top;
 int data[string];int seen;
 function automatic int update(ref int items[string]);
  items["new"]=7;items.delete("old");return items.num();
 endfunction
 function automatic int inspect(const ref int items[string]);int total;total=0;foreach(items[k])total+=items[k];return total;endfunction
 initial begin data["old"]=3;data["keep"]=5;seen=update(data);$display("TRACE basic %0d %0d %0d %0d",seen,data.exists("old"),data["new"],inspect(data));end
 endmodule
