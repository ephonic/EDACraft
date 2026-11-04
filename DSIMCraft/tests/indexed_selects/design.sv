`timescale 1ps/1ps
module top;
parameter W=4;
reg [15:0] q;
reg [19:4] based;
reg [127:0] wide;
reg [127:0] bigindex;
reg [7:0] i,j;
reg [7:0] result;
reg [15:0] sampled;
initial begin
 q=16'hc35a;based=16'hc35a;wide=128'h0123456789abcdef_fedcba9876543210;i=4;j=2;bigindex=4;sampled=0;
 $display("TRACE reads=%b %h %h %h %h",q[i],q[i+:W],q[i-:W],based[i+:8],wide[bigindex+:80]);
 $display("TRACE folded=%h %h %h",q[3+1+:2+2],q[4+3:4],q[i+1+:W]);
 i=14;
 $display("TRACE partial=%b %b %b",q[i+:4],based[j+:8],q[j-:4]);
 q[i+:4]=4'b10xz;based[j+:8]=8'hf0;q[j-:4]=4'b1010;
 $display("TRACE clipped=%h %h",q,based);
 i=8'hxx;
 $display("TRACE unknown=%b %b",q[i],wide[i+:80]);
 q[i]=0;q[i+:8]=8'hff;
 i=8'hzz;based[i-:8]=0;
 bigindex=255;
 $display("TRACE large=%b %b",q[bigindex],wide[bigindex+:16]);
 wide[bigindex+:80]=0;
 $display("TRACE unchanged=%h %h %h",q,based,wide);
 i=4;wide[i+:80]=80'hxz0123456789abcdef01;
 $display("TRACE widewrite=%h %b",wide,wide[i+:80]);
 // The rightmost concatenation item wins on overlapping variable targets.
 i=4;j=6;q=0;{q[i+:8],q[j+:4],q[i]}=13'h1cab;
 $display("TRACE overlap=%h",q);
 // NBA samples both RHS and variable target at issue.
 q=0;i=3;q[i]<=1;i=7;q[i+:4]<=#3 4'ha;i=1;
 #1;$display("TRACE nba=%h",q);
 #3;$display("TRACE delayed=%h",q);
 // Blocking intra-assignment samples RHS now and target after the wait.
 i=2;result=8'ha5;q[i+:8]=#4 result;
 $display("TRACE blocking=%h index=%d",q,i);
 // Unknown/out-of-range destinations remain no-ops, including pending NBAs.
 i=255;q[i]<=#1 1;q[i+:8]<=#1 8'hff;
 #2;$display("TRACE final=%h",q);
 $finish;
end
initial begin #5;i=6;result=8'h3c;end
endmodule
