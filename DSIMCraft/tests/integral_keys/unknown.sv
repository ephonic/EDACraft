module top;
 typedef bit [128:0] K;int values[K];logic [128:0] key;
 initial begin key='0;key[128]=1'bx;values[key]=9;$display("BAD unknown index accepted");end
endmodule
