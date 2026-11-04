`timescale 1ps/1ps
module child(input [3:0] d,output [3:0] y);assign y=d;endmodule
module top;
reg[15:0] q;
reg[7:0] i;
wire[3:0] selected,ported;
child u(q[i+:4],ported);
assign selected=q[i+:4];
initial begin
 q=16'hc35a;i=4;
 #1;$display("TRACE first=%h port=%h",selected,ported);
 i=8;
 #1;$display("TRACE index=%h",selected);
 q[i+:4]=4'h9;
 #1;$display("TRACE changed=%h q=%h",selected,q);
 i=15;
 #1;$display("TRACE upper=%b",selected);
 i=8'hxx;
 #1;$display("TRACE x=%b",selected);
 q[i]<=#2 0;
 i=0;
 #3;$display("TRACE ignored=%h",q);
 $finish;
end
endmodule
