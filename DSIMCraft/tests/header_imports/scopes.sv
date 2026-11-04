`timescale 1ns/1ps
package imported_scope;parameter integer WIDTH=7;endpackage
package unused_scope;parameter integer WIDTH=9;endpackage
module shadow import imported_scope::*; import unused_scope::*;
 #(parameter integer WIDTH=11)(output logic [WIDTH-1:0] value);
 initial begin value=0;#1;value=WIDTH;end
endmodule
module repeated import imported_scope::WIDTH; import imported_scope::WIDTH;
 #(parameter integer N=WIDTH)(output logic [N-1:0] value);
 import imported_scope::WIDTH;
 initial begin value=0;#1;value=WIDTH;end
endmodule
module top;
 wire [10:0] a;wire [6:0] b;
 shadow one(a);repeated two(b);
 initial begin #2;
  if(a!==11||b!==7)$fatal(1,"header import shadow/repeated binding");
  $display("TRACE header scopes %h %h",a,b);
 end
endmodule
