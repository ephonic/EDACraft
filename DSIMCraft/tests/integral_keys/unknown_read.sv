module top;
 typedef bit [128:0] K;int values[K];logic [128:0] key;int observed;
 initial begin key='0;key[128]=1'bx;observed=values[key];$display("BAD unknown read accepted");end
endmodule
