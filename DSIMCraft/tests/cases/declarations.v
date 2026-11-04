module top;
  parameter W=8;
  reg [W-1:0] q=8'd3;
  wire [W-1:0] y=q;
  initial begin
    #1 $display("TRACE q=%0d y=%0d",q,y);
    q=8'd5;
    #1 $display("TRACE q=%0d y=%0d",q,y);
    $finish;
  end
endmodule
