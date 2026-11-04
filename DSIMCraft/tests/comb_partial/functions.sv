`timescale 1ns/1ps
module top;
logic [7:0] d,q,seen;
logic flag;
function automatic logic [7:0] decorate();
  q=d;q[7]=flag;return q;
endfunction
function automatic logic [7:0] nested();return decorate();endfunction
always_comb seen=nested();
initial begin
 d=8'h12;flag=0;
 #1;$display("TRACE functions %b %b",q,seen);
 d=8'h63;flag=1;
 #1;$display("TRACE functions %b %b",q,seen);
 d=8'bxz010101;flag=1'bz;
 #1;$display("TRACE functions %b %b",q,seen);$finish;
end
endmodule
