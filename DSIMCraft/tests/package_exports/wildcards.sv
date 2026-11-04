`timescale 1ns/1ps
package source_pkg;
 parameter int USED=3,HIDDEN=9;
endpackage
package selected;
 export source_pkg::*;
 import source_pkg::*;
 localparam int COPY=USED;
endpackage
package all_imports;
 export *::*;
 import source_pkg::HIDDEN;
endpackage
package forward;
 export source_pkg::USED;
 import source_pkg::*;
endpackage
package unimported;
 export absent::*;
endpackage
package outer_pkg;
 import selected::*;
 parameter int LOCAL=USED+1;
 export *::*;
endpackage
module top;
 import outer_pkg::*;
 import forward::*;
 parameter int HIDDEN=7;
 integer value;
 initial begin
  value=USED+LOCAL+HIDDEN+all_imports::HIDDEN;
  #1;if(value!=23||selected::USED!=3||forward::USED!=3)$fatal(1,"wildcard export filtering");
  $display("TRACE export wildcards %0d %0d %0d %0d",USED,LOCAL,HIDDEN,value);
 end
endmodule
