`timescale 1ns/1ps
module lane #(parameter K=0)(input [7:0] a,output [7:0] y);
  generate
    if (K==0) begin: zero
      assign y = a;
    end else begin: nonzero
      wire [7:0] k = K;
      assign #1 y = a ^ k;
    end
  endgenerate
endmodule
module bank #(parameter N=4, MODE=1)(input clk,input [31:0] a,output [31:0] y,output [31:0] q);
  genvar i;
  generate
    for (i=0;i<N;i=i+1) begin: lanes
      wire [7:0] temp;
      reg [7:0] saved;
      lane #(.K(i)) u(a[i*8+:8], temp);
      always @(posedge clk) saved <= #2 temp;
      assign q[i*8+:8]=saved;
      if (MODE) begin: active
        assign y[i*8+:8]=temp;
      end else begin: inactive
        missing_module unused();
      end
    end
    case (MODE)
      0: begin: off initial $display("BAD"); end
      1,2: begin: on wire marker=1'b1; end
      default: begin: other wire marker=1'b0; end
    endcase
    if (0) begin: absent missing_module bad(); end
  endgenerate
endmodule
module top;
  reg clk;
  reg [31:0] a;
  wire [31:0] y,q;
  bank u(clk,a,y,q);
  initial begin
    clk=0;a=32'h10203040;
    #2 $display("TRACE y=%h q=%h",y,q);
    clk=1;#3 $display("TRACE q=%h",q);
    clk=0;a=32'hffeeddcc;
    #2 clk=1;
    #3 $display("TRACE y=%h q=%h",y,q);
    $finish;
  end
endmodule
