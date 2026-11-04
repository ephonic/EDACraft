module count #(parameter W=4, parameter START=0)(input clk, output reg [W-1:0] q=START);
  always @(posedge clk) q<=q+1'b1;
endmodule
module group(input clk, output [3:0] a,output [7:0] b);
  count #(.W(4),.START(14)) c0(clk,a);
  count #(.W(8),.START(20)) c1(.clk(clk),.q(b));
endmodule
module top;
  reg clk;
  wire [3:0] a;
  wire [7:0] b;
  group g(clk,a,b);
  initial begin
    clk=0;
    #1 clk=1;
    #1 $display("TRACE a=%0d b=%0d",a,b);
    clk=0;
    #1 clk=1;
    #1 $display("TRACE a=%0d b=%0d",a,b);
    $finish;
  end
endmodule
