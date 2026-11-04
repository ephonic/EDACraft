module top;
  reg clk;
  reg rst;
  reg [7:0] q;
  wire [7:0] plus;
  assign plus = q + 8'd1;
  initial begin
    clk=0; rst=1;
    #2 rst=0;
    #20 $finish;
  end
  always #1 clk=~clk;
  always @(posedge clk) begin
    if (rst) q <= 0;
    else q <= plus;
  end
  initial begin
    #4 $display("TRACE q=%0d plus=%0d",q,plus);
    #4 $display("TRACE q=%0d plus=%0d",q,plus);
    #4 $display("TRACE q=%0d plus=%0d",q,plus);
    #4 $display("TRACE q=%0d plus=%0d",q,plus);
  end
endmodule
