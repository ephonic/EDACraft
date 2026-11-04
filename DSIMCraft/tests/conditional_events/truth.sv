`timescale 1ns/1ps
module top;
logic clk=0;logic[3:0]guard=0;logic[129:0]wide=0;
integer rises=0,falls=0,changes=0,wides=0;
always @(posedge clk iff guard) rises++;
always @(negedge clk iff guard) falls++;
always @(clk iff guard) changes++;
always @(posedge clk iff wide) wides++;
initial begin
#1 guard=1;wide[129]=1;
#1 clk=1;#1 clk=0;
#1 guard=0;clk=1;
#1 clk=0;guard=4'bx000;wide=0;
#1 clk=1;
#1 clk=0;guard=4'bx001;wide={130{1'bx}};wide[129]=1;
#1 clk=1;#1 clk=0;
#1 guard=4'bzzzz;clk=1;
#1 clk=0;guard=2;wide=0;
#1 clk=1;#1 clk=0;
#1 $display("TRACE truth %0d %0d %0d %0d",rises,falls,changes,wides);
if(rises!==3||falls!==5||changes!==8||wides!==4)$fatal(1,"truth mismatch");$finish;
end
endmodule
