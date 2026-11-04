module top;
 import "DPI-C" function void packed_transfer(input logic [128:0] a,output logic [128:0] b,inout bit [64:0] c);
 import "DPI-C" function void single(input logic [0:0] a,output logic [0:0] b);
 import "DPI-C" function int integer_value(input integer a);
 import "DPI-C" function void fill_time(output time a);
 logic [128:0] a,b;bit [64:0] bits;logic [0:0] one;time t;
 initial begin
  a={1'bx,32'hzzzzzzzz,32'h12345678,32'hxxxxxxxx,32'h87654321};bits=65'h123456789abcdef01;
  packed_transfer(a,b,bits);single(1'bz,one);fill_time(t);
  if(b!==a||one!==1'bz||t!==64'h1234567887654321)$fatal(1,"DPI vector mismatch");
  $display("TRACE vector %b %h %0d",b===a,bits,integer_value(32'b11110000xxxxzzzz11110000xxxxzzzz));
  #1;a=0;packed_transfer(a,b,bits);$display("TRACE vector2 %h %h",b,bits);$finish;
 end
endmodule
