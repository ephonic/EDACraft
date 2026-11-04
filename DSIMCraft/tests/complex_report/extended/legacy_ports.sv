module legacy(a,q);
  input [7:0] a;
  output [7:0] q;
  reg [7:0] q;
  always @*q=a+1;
endmodule
module tb;
  reg [7:0]a=8'd6;
  wire [7:0]q;
  legacy u(a,q);
  initial begin #1;if(q!==7)$fatal(1,"legacy split port");$display("TRACE legacy %0d",q);$finish;end
endmodule
