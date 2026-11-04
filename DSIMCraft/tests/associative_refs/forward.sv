module top;
 int data[int];int seen;
 function automatic void leaf(ref int items[int]);items[-3]=9;items[7]=4;endfunction
 function automatic void middle(ref int items[int]);leaf(items);endfunction
 function automatic int sum(const ref int items[int]);int total;total=0;foreach(items[k])total+=items[k];return total;endfunction
 function automatic int reader(const ref int items[int]);return sum(items);endfunction
 initial begin middle(data);seen=reader(data);$display("TRACE forward %0d %0d",seen,data.num());end
 endmodule
