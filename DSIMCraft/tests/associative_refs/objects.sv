module top;
 class Store;int values[string];endclass
 Store left,right;int seen;
 function automatic void change(ref int items[string]);items["x"]=11;items["y"]=13;endfunction
 initial begin left=new();right=new();change(left.values);change(right.values);right.values["x"]=19;seen=left.values["x"]+right.values["x"];$display("TRACE objects %0d %0d %0d",seen,left.values.num(),right.values["y"]);end
 endmodule
