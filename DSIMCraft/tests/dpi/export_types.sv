module top;
 import "DPI-C" context function int typed_gateway();
 export "DPI-C" function typed;
 export "DPI-C" function empty;
 export "DPI-C" function greeting;
 int calls=0,result;
 function automatic int typed(input byte a,output longint b,inout string text,output logic [96:0] vector,inout bit [64:0] bits);
  b=a-64'sd10000000000;text={text,"!"};vector={1'b1,32'hzzzzzzzz,32'hxxxxxxxx,32'h12345678};bits^=65'h1fedcba9876543210;
  return a+3;
 endfunction
 function automatic void empty();repeat(2)calls++;endfunction
 function automatic string greeting();return "hello export";endfunction
 initial begin
  result=typed_gateway();$display("TRACE exports %0d %0d",result,calls);
  if(result!=42||calls!=2)$fatal(1,"DPI export conversions");
  #1;result=typed_gateway();$display("TRACE repeat %0d %0d",result,calls);$finish;
 end
endmodule
