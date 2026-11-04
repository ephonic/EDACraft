package pkg;
class C;
extern function int f(C requested_type, string requested_type_name, int match_type_pair);
function int g(); return f(.match_type_pair(2),.requested_type(null),.requested_type_name("x"));endfunction
endclass
function int C::f(C requested_type, string requested_type_name, int match_type_pair);
return requested_type==null ? match_type_pair : 0;
endfunction
endpackage
module top; import pkg::*;
C c; int q;
initial begin c=new; q=c.g();$display("TRACE named %0d",q);end
endmodule
