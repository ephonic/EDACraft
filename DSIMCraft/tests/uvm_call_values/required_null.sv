package p;
class C;endclass
function int check(C object);return object==null ? 17 : 9;endfunction
function int named(C object, int value=23);return object==null ? value : 0;endfunction
endpackage
module top;
 import p::*;
 int result;
 initial begin
  result=check(null);$display("TRACE positional %0d",result);
  result=named(.object(null));$display("TRACE required %0d",result);
 end
endmodule
