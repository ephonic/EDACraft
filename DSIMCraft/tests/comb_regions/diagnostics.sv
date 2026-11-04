`timescale 1ns/1ps
module top;
logic [1:0] a=0;
wire x=a[0],y=a[1],z=^a;
integer q;
always_comb begin
 unique if(x)q=1;else if(y)q=2;
end
initial begin
 #1;a=1;#0;a=2;#1;a=3;#1;a=0;#1;
 if(q!==1)$fatal(1,"qualified selection after batch");
 $display("TRACE diagnostics %b %b %b %0d",x,y,z,q);
end
endmodule
