module top;
  reg clk;
  reg [3:0] a,b;
  reg seen;
  initial begin
    clk=0;a=1;b=2;seen=0;
    #1 clk=1;
    #0 $display("TRACE inactive a=%0d b=%0d",a,b);
    #1 $display("TRACE committed a=%0d b=%0d seen=%b",a,b,seen);
    clk=0;
    #1 clk=1;
    #1 $display("TRACE swapped a=%0d b=%0d",a,b);
    $finish;
  end
  always @(posedge clk) begin a<=b; b<=a; end
  always @(a or b) seen=1;
endmodule
