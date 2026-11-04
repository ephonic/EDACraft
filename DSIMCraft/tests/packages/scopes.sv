`timescale 1ns/1ps
package first;
 parameter int WIDTH=5;
 parameter int CLASH=11;
 function automatic integer apply(integer value);return value+WIDTH;endfunction
endpackage
package second;
 parameter int CLASH=22;
 parameter int OFFSET=9;
endpackage
module leaf #(parameter integer N=2)(output integer value);
 import first::*;
 import second::*;
 localparam int CLASH=3;
 task automatic run(output integer result);
  import second::OFFSET;
  integer local_value;
  begin local_value=apply(N);#1;result=local_value+OFFSET+CLASH;end
 endtask
 initial run(value);
endmodule
module top;
 integer one,two;
 leaf #(.N(2)) a(one);leaf #(.N(4)) b(two);
 initial begin
  #2;if(one!=19||two!=21)$fatal(1,"cloned imports and lexical shadow");
  begin : block_scope
   import second::CLASH;
   integer local_value;
   local_value=CLASH;
   if(local_value!=22)$fatal(1,"block import");
  end
  $display("TRACE package scopes %0d %0d",one,two);
 end
endmodule
