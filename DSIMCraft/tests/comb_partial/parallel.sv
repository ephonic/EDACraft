`timescale 1ns/1ps
module island #(parameter BASE=1)(output logic[7:0] result);
logic [7:0] a,q;
logic flag;
always_comb begin q=a;q[7]=flag;result=q;end
initial begin
 a=BASE;flag=0;
 #1;a=a+1;flag=1;
 #1;a=a+1;flag=0;
 #1;
end
endmodule
module top;
wire [7:0] one,two;
island #(1) a(one);
island #(17) b(two);
endmodule
