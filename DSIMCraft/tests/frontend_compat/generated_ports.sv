`timescale 1ns/1ps
module lanes #(parameter N=2, W=8)(input wire [N-1:0][W-1:0] a,output wire [N-1:0][W-1:0] y);
  genvar i;
  generate for(i=0;i<N;i++)begin:lane
    wire [W-1:0] local_value;
    assign local_value=a[i]+i;
    assign y[i]=local_value;
  end endgenerate
endmodule
module compatibility_tb;
  logic [1:0][7:0] a;
  wire [1:0][7:0] y;
  wire [2:0][3:0] narrow;
  lanes first(a,y);
  lanes #(.N(3),.W(4)) second(12'h123,narrow);
  initial begin
    a=16'h1234;#1;
    if(y!==16'h1334||narrow!==12'h333) $fatal(1,"parameter clone/ports");
    $display("TRACE generated %h %h",y,narrow);
    a[0]=8'hfe;#1;
    if(y!==16'h13fe) $fatal(1,"port row store");
    $display("TRACE generated update %h",y);
    $finish;
  end
endmodule
