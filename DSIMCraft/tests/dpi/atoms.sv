module top;
 import "DPI-C" function byte echo_byte(input byte x);
 import "DPI-C" function shortint unsigned echo_short(input shortint unsigned x);
 import "DPI-C" function longint sum_long(input longint a,input longint b);
 import "DPI-C" function longint unsigned echo_ulong(input longint unsigned x);
 import "DPI-C" function logic echo_logic(input logic x);
 import "DPI-C" function bit invert_bit(input bit x);
 import "DPI-C" function string decorate(input string x);
 import "DPI-C" function void copy_text(input string x,output string y);
 import "DPI-C" function void out_args(input int x,output int y,inout longint z);
 import "DPI-C" pure pure_twice = function int twice(input int x);
 int a;longint b;string message;
 initial begin
  b=-20;out_args(9,a,b);copy_text("retained",message);
  $display("TRACE atoms %0d %0d %0d %h",echo_byte(-7),echo_short(16'hfedc),sum_long(-64'sd5000000000,3),echo_ulong(64'hfedcba9876543210));
  $display("TRACE scalar %b %b %b %b %b",echo_logic(1'b0),echo_logic(1'b1),echo_logic(1'bx),echo_logic(1'bz),invert_bit(1'bx));
  $display("TRACE out %0d %0d %s %s",a,b,decorate("hello"),message);
  #2;a=twice(11);$display("TRACE alias %0d",a);$finish;
 end
endmodule
