`timescale 1ns/1ps
package first_pkg;
 parameter N=3;typedef logic[4:0] T;
 function automatic integer f(input integer x);return x+N;endfunction
endpackage
module before_import;parameter N=19;integer v;initial v=N;endmodule
import first_pkg::*;
module early(output integer value);initial value=f(N);endmodule
package late_pkg;parameter EXTRA=11;endpackage
import late_pkg::EXTRA;
interface automatic bus #(parameter W=N);T data;function integer calc(input integer n);return f(n)+EXTRA;endfunction endinterface
module shadow;
 parameter N=7;typedef logic[2:0] T;
 function automatic integer f(input integer x);return x+100;endfunction
 T v;integer answer;initial begin v=N;answer=f(1);end
endmodule
module top;
 parameter N=23;
 integer value;T x=5'h1f;
 before_import before_i();early a(value);shadow b();bus #(9) c();
 initial begin c.data=x;#1;
 if(value!=6||before_i.v!=19||b.v!=7||b.answer!=101||c.calc(2)!=16||c.data!=31)$fatal(1,"unit lexical bindings");
 $display("TRACE unit lexical %0d %0d %0d %0d %0d",value,b.v,c.calc(2),f(1),N);
 end
endmodule
