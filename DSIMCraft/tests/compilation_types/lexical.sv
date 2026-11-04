`timescale 1ps/1ps
package values_pkg;parameter VALUE=11;typedef bit[4:0] Element;endpackage
import values_pkg::VALUE,values_pkg::Element;
class C;
 Element n=VALUE;
 function int read();return n;endfunction
endclass
module local_scope;
 class C;
  int n=17;
  function int read();return n;endfunction
 endclass
 C x;
 initial x=new;
endmodule
package extra_pkg;parameter EXTRA=4;endpackage
import extra_pkg::*;
class Later extends C;
 function int read();return super.read()+EXTRA;endfunction
endclass
module top;
 parameter VALUE=99;
 local_scope local_i();C x;Later y;
 int observed;
 initial begin
  x=new;y=new;#1;observed=y.read();
  if(x.read()!=11||y.read()!=15||local_i.x.read()!=17||VALUE!=99)
   $fatal(1,"compilation lexical context or module shadowing");
  $display("TRACE unit lexical %0d %0d %0d",x.read(),y.read(),local_i.x.read());
 end
endmodule
