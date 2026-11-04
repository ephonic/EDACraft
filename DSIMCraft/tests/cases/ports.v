module top(q);
  output [7:0] q;
  reg [7:0] q;
  reg [7:0] fill;
  initial begin
    q=8'd9;fill='1;
    #1 $display("TRACE q=%0d fill=%h",q,fill);
    $finish(0);
  end
endmodule
