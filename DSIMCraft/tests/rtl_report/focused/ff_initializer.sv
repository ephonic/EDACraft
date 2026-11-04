module top;logic clk=0;logic q=0;always #1 clk=~clk;always_ff @(posedge clk)q<=~q;initial begin #4;$display("TRACE ff %b",q);$finish;end endmodule
