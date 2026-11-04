`timescale 1ns/1ps
package first_binding;parameter integer X=11;endpackage
package second_binding;parameter integer X=22;endpackage
module top;
 import first_binding::*;
 integer early;
 initial early=X;
 import second_binding::*;
 integer later;
 initial later=X;
 initial begin
  #1;if(early!=11||later!=11)$fatal(1,"wildcard binding must survive later wildcard imports");
  $display("TRACE package bindings %0d %0d",early,later);
 end
endmodule
