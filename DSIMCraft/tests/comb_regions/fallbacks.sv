`timescale 1ns/1ps
module top;
logic [7:0] a=0;integer calls=0;
function [7:0] effect(input [7:0] value);
 calls=calls+1;effect=value+calls;
endfunction
wire [7:0] x,y,z;
assign x=a+1;
always @(a)$display("TRACE between %h %h %h",x,y,z);
assign y=a+2;
assign z=effect(a);
wire feedback;
assign feedback=a[0]?feedback:1'b0;
wire driven;
assign driven=a[0];
assign driven=a[1];
initial begin
 #1;a=2;#1;a=3;#1;a=4;#1;
 if(x!==5||y!==6||calls!==4||feedback!==0)$fatal(1,"fallback values");
 $display("TRACE fallback %h %h %h %0d %b",x,y,z,calls,driven);
end
endmodule
