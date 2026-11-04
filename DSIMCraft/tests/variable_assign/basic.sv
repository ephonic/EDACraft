`timescale 1ns/1ps
module top;
 logic signed [7:0] d;
 logic signed [15:0] q;
 bit [7:0] b;
 integer n;
 logic [7:0] truncated;
 assign q=d,b=d,n=d,truncated=q;
 initial begin
  d=-8'sd3;
  #1 $display("TRACE basic %h %h %h %h",q,b,n,truncated);
  if(q!==16'hfffd||b!==8'hfd||n!==-3||truncated!==8'hfd)$fatal(1,"signed assignment");
  d=8'bx01z10x1;
  #1 $display("TRACE unknown %b %b %b",q,b,truncated);
  if(q!==16'bxxxxxxxxx01z10x1||b!==8'b00101001||truncated!==8'bx01z10x1)$fatal(1,"unknown assignment");
  d=8'h2a;
  #1 $display("TRACE final %h %h %h %h",q,b,n,truncated);
  if(q!==42||b!==42||n!==42||truncated!==42)$fatal(1,"final assignment");
  $finish;
 end
endmodule
