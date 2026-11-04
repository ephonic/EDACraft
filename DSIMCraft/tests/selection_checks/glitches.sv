`timescale 1ns/1ps
module top;
logic a=0,n;integer q,r;
always_comb n=!a;
always_comb unique if(a)q=1;else if(n)q=2;
always_comb unique case(1'b1) a:r=1;n:r=2;endcase
initial begin
 #1;a=1;#1;a=0;#1;
 if(q!==2||r!==2)$fatal(1,"stable branch");
 $display("TRACE glitches %0d %0d",q,r);
end
endmodule
