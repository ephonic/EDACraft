`timescale 1ns/1ps
package math_pkg;
 localparam int BIAS=7;
 typedef logic[15:0] word_t;
 function automatic integer helper(integer x);return x+BIAS;endfunction
 function automatic word_t convert(word_t x);return word_t'(helper(int'(x))*2);endfunction
 function integer count(input integer step);
  static integer n=0;
  begin n=n+step;return n;end
 endfunction
 task automatic delayed(word_t x,output word_t y);begin #2;y=convert(x);end endtask
endpackage
package wrapper;
 import math_pkg::*;
 function automatic integer helper(integer x);return int'(convert(math_pkg::word_t'(x)));endfunction
endpackage
module lane(output integer value);
 import math_pkg::*;
 localparam int BIAS=1000;
 function automatic integer helper(integer x);return x+999;endfunction
 initial begin value=count(1);#1;value=count(2);end
endmodule
module top;
 import math_pkg::*;
 integer one,two;math_pkg::word_t value,other;
 lane a(one),b(two);
 initial begin
  value=convert(5);
  if(value!=24||wrapper::helper(3)!=20)$fatal(1,"package lexical binding");
  delayed(value,other);
  if(other!=62||one+two!=10||math_pkg::count(0)!=6)$fatal(1,"shared package static function state");
  $display("TRACE package functions %0d %0d %0d",value,other,one+two);
 end
endmodule
