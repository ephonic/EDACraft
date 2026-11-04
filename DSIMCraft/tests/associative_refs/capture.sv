module top;
 class Store;int values[string];endclass
 Store first,second,current;int calls,seen;
 function automatic Store choose();calls++;return current;endfunction
 task automatic change(ref int items[string]);#2;items["x"]=23;endtask
 initial begin first=new();second=new();current=first;fork change(choose().values);begin #1;current=second;end join
 seen=first.values["x"];$display("TRACE capture %0d %0d %0d",calls,seen,second.values.num());end
 endmodule
