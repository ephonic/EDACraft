`timescale 1ns/1ps
module top;
logic [7:0] a=0;
wire [7:0] x,y,z;
assign #1 x=a+1;
assign #1 y=a+2;
assign #1 z=a+3;
initial begin #2;a=2;#2;
 if(x!==3||y!==4||z!==5)$fatal(1,"delay");
 $display("TRACE delay %h %h %h",x,y,z);
end
endmodule
