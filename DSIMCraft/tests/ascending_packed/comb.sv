`timescale 1ns/1ps
module top;
logic[0:7] q;logic[0:7] y;integer index;
always_comb q[0:3]=q[4:7];
always_comb y={q[index+:4],4'b0};
initial begin
 index=4;#1;q[4:7]=4'h6;#1;$display("TRACE COMB %h %h",q,y);
 index=2;#1;$display("TRACE COMB %h %h",q,y);
 q[4:7]=4'ha;#1;$display("TRACE COMB %h %h",q,y);$finish;
end
endmodule
