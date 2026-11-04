// Independent functional Verilog references; no dsim-generated functions.
// This ideal Liberty model uses consensus for ambiguous clocks and controls.
primitive seq_dff(Q,D,C);
output Q; reg Q; input D,C;
table
0 (01) : ? : 0;
1 (01) : ? : 1;
0 (0x) : 0 : 0;
1 (0x) : 1 : 1;
0 (x1) : 0 : 0;
1 (x1) : 1 : 1;
? (?0) : ? : -;
? (1x) : ? : -;
* ? : ? : -;
endtable
endprimitive
primitive seq_latch(Q,D,G);
output Q; reg Q; input D,G;
table
? 0 : ? : -;
0 1 : ? : 0;
1 1 : ? : 1;
0 x : 0 : 0;
1 x : 1 : 1;
endtable
endprimitive
module DFFP(input C,D,output Q,QN); seq_dff f(Q,D,C); assign QN=~Q; endmodule
module DFFN(input C,D,output Q,QN); wire n; assign n=~C; seq_dff f(Q,D,n); assign QN=~Q; endmodule
module LATCHP(input G,D,output Q,QN); seq_latch f(Q,D,G); assign QN=~Q; endmodule
module LATCHN(input G,D,output Q,QN); wire n; assign n=~G; seq_latch f(Q,D,n); assign QN=~Q; endmodule
// Attribute truth tables expressed with Verilog's four-state conditional merge.
// A separate two-state value is retained for each Liberty state variable.
module seq_async_model #(parameter LATCH=0, parameter ACTION=0)
(input C,D,R,S,output reg Q,QN);
reg last, nq, nn;
wire data_value = D===1'bz ? 1'bx : D;
wire control = C===1'bz ? 1'bx : C;
initial last=1'bx;
always @(control or R or S or (LATCH ? data_value : 1'b0)) begin
 nq=Q; nn=QN;
 if (LATCH) begin nq=control?data_value:Q; nn=control?~data_value:QN; end
 else if(last===1'b0 && control===1'b1) begin nq=data_value; nn=~data_value; end
 else if((last===1'b0 && control===1'bx)||(last===1'bx && control===1'b1)) begin
  nq=1'bx ? data_value:Q; nn=1'bx ? ~data_value:QN;
 end
 // ACTION 0: conflict 00; ACTION 1: toggle/hold; ACTION 2: conflict 01.
 Q<=R?(S?(ACTION==1?~Q:1'b0):1'b0):(S?1'b1:nq);
 QN<=R?(S?(ACTION==1?QN:ACTION==2?1'b1:1'b0):1'b1):(S?1'b0:nn);
 last=control;
end
endmodule
module DFFR(input C,D,R,output Q,QN); seq_async_model f(C,D,R,1'b0,Q,QN); endmodule
module DFFS(input C,D,S,output Q,QN); seq_async_model f(C,D,1'b0,S,Q,QN); endmodule
module DFFSR(input C,D,R,S,output Q,QN); seq_async_model f(C,D,R,S,Q,QN); endmodule
module DFFTN(input C,D,R,S,output Q,QN); seq_async_model #(.ACTION(1)) f(C,D,R,S,Q,QN); endmodule
module LATCHR(input G,D,R,output Q,QN); seq_async_model #(.LATCH(1)) f(G,D,R,1'b0,Q,QN); endmodule
module SRLATCH(input R,S,output Q,QN); seq_async_model #(.LATCH(1),.ACTION(2)) f(1'b0,1'b0,R,S,Q,QN); endmodule
module DFFE(input C,D,E,output Q,QN); wire n; assign n=(D&E)|(Q&~E); seq_dff f(Q,n,C); assign QN=~Q; endmodule
module TFF(input C,R,output Q,QN); wire n; assign n=~Q; DFFR f(C,n,R,Q,QN); endmodule
module DFFOUT(input C,D,A,E,output Q,QN,Y,TQ);
DFFP f(C,D,Q,QN); assign Y=Q&A; assign TQ=E?Q:1'bz;
endmodule
