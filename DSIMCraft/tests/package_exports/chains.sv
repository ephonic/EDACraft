`timescale 1ns/1ps
package origin;
 parameter int W=5;
 typedef logic signed[W-1:0] T;
 function automatic integer calc(integer x);return x+W;endfunction
endpackage
package left;
 import origin::*;
 export origin::W,origin::T,origin::calc;
endpackage
package right;
 export *::*;
 import origin::T,left::W,left::calc;
endpackage
package public_api;
 import right::*;
 export right::T,right::W,right::calc;
endpackage
module leaf import public_api::*; #(parameter N=W)(output integer value);
 localparam int OFFSET=20;
 initial begin value=0;#1;value=calc(N)+OFFSET;end
endmodule
module top;
 import origin::*;
 import left::*;
 import public_api::*;
 integer a,b;
 T sample;
 leaf #(2) x(a);leaf #(4) y(b);
 initial begin
  sample=-2;
  #2;if(a!=27||b!=29||sample!=-2||calc(3)!=8)$fatal(1,"diamond exports");
  $display("TRACE export chains %0d %0d %0d %0d",a,b,sample,calc(3));
 end
endmodule
