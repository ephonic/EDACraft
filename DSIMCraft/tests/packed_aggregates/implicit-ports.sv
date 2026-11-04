`timescale 1ns/1ps
module invert(input wire a,output wire y);assign y=~a;endmodule
module top;logic a=0;wire y;invert u(.y,.a);
initial begin #1;if(y!==1)$fatal(1,"implicit port initial");a=1;#1;if(y!==0)$fatal(1,"implicit port update");$display("TRACE implicit ports pass");end
endmodule
