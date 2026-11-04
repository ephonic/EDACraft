module top;
  reg clk;
  reg [3:0] pos,neg,both;
  initial begin
    pos=0;neg=0;both=0;
    #1 clk=0;
    #1 clk=1;
    #1 clk=1'bx;
    #1 clk=1;
    #1 clk=1'bz;
    #1 clk=0;
    #1 $display("TRACE pos=%0d neg=%0d both=%0d",pos,neg,both);
    $finish;
  end
  always @(posedge clk) pos<=pos+4'd1;
  always @(negedge clk) neg<=neg+4'd1;
  always @(posedge clk or negedge clk) both<=both+4'd1;
endmodule
