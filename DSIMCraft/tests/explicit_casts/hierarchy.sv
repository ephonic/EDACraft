`timescale 1ns/1ps
module lane #(parameter int W=9,parameter longint P=longint'(32'hffffffff+1))(output logic [129:0] q);
localparam V=(W+1)'(-1);
genvar g;
generate for(g=0;g<2;g=g+1)begin:gen
 localparam C=(W+g)'(32'hffffffff);
 logic [W:0] value;
 initial begin value=(W+1)'(C);#1;value=byte'(C);end
end endgenerate
initial begin q=130'(V);#2;q=130'(P);#2;q=130'(signed'(8'h80));end
endmodule
module top;
wire [129:0] a,b;
lane #(.W(7))u(a);
lane #(.W(12),.P(longint'(32'hffffffff+2)))v(b);
initial begin #5;$display("TRACE hierarchy %h %h",a,b);$finish;end
endmodule
