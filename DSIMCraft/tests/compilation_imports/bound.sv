`timescale 1ns/1ps
package p;parameter N=3;endpackage
package q;parameter N=5;endpackage
import p::*;
module early(output integer v);initial v=N;endmodule
import q::*;
module top #(parameter EARLY=N)();integer v;integer result;early e(v);
 initial begin #1;result=N;if(v!=3||result!=3||EARLY!=3)$fatal(1,"unit prior binding");$display("TRACE unit bound %0d %0d",v,result);end
endmodule
