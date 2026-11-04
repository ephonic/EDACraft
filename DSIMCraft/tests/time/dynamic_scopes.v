`timescale 10ns/1ns
module coarse;
reg [7:0] d,q;
initial begin d=2; q=0; q <= #(d) 8'h42; #(d+8'd1);
  $display("TRACE coarse t=%0t q=%h",$time,q);
end
endmodule
`timescale 1ns/1ps
module top;
coarse c();
reg [7:0] d,q;
initial begin d=3; q=0; q = #(d) 8'h21; #(d+8'd1);
  $display("TRACE fine t=%0t q=%h",$time,q);
end
endmodule
