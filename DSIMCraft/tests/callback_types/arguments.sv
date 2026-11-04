class Base;
 int value=2;virtual function int kind();return 1;endfunction
endclass
class Derived extends Base;
 function int kind();return 7;endfunction
endclass
module top;
 Base base,copy;Derived derived,down;int stage=0;
 function automatic int inspect(input Base value);return value.kind();endfunction
 function automatic void pass(output Base value,input Derived source);value=source;endfunction
 function automatic void set_value(ref Base value);value.value=17;endfunction
 initial begin
  derived=new();base=derived;pass(copy,derived);set_value(base);
  $display("TRACE args %0d %0d %0d",inspect(derived),copy==base,derived.value);stage++;#1;
  if(!$cast(down,base))$fatal(1,"cast failed");$display("TRACE cast %0d %0d",down==derived,down.kind());$finish;
 end
endmodule
