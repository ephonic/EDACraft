module top;
 function unsigned low_bit(input int value);return value;endfunction
 function automatic unsigned [8:0] nine_bits(input int value);return value;endfunction
 function signed [8:0] signed_bits(input int value);return value;endfunction
 class C;
  extern function unsigned flag(input int value);
 endclass
 function unsigned C::flag(input int value);return value;endfunction
 C object;
 int a,b,c;
 initial begin
  object=new();a=low_bit(3);b=nine_bits(256);c=signed_bits(256);
  if($bits(low_bit(0))!=1 || a!=1 || b!=256 || c!=-256 || object.flag(2)!=0)$fatal(1,"implicit unsigned function type");
  $display("TRACE implicit unsigned a=%0d b=%0d c=%0d",a,b,c);$finish;
 end
endmodule
