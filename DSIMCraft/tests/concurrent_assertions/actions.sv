`timescale 1ns/1ps
module top;
 reg clk=0,q=0;integer pass=0,fail=0;
 always #5 clk=~clk;
 always @(posedge clk) q<=~q;
 a: assert property(@(posedge clk) !q) begin
   if(q!==1'b1)$fatal(1,"action must see NBA value");pass=pass+1;$display("TRACE action pass %0d",q);
 end else begin
   if(q!==1'b0)$fatal(1,"failure action must see NBA value");fail=fail+1;$display("TRACE action fail %0d",q);
 end
 initial begin #31;$display("TRACE actions %0d %0d",pass,fail);$finish;end
endmodule
