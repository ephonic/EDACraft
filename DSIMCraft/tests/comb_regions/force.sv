`timescale 1ns/1ps
module top;
logic [7:0] a=0;
wire [7:0] x=a+1,y=a+2,z=a+3;
initial begin
 #1;force x=8'h42;a=2;#1;
 if(x!==8'h42||y!==4||z!==5)$fatal(1,"force");
 release x;#1;
 if(x!==3)$fatal(1,"release");
 $display("TRACE force %h %h %h",x,y,z);
end
endmodule
