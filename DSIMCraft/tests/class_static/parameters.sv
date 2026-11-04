package p;
 class C #(type T=int, parameter int N=1);
  static int count=N;
  static function int add(int x=1);count+=x;return count;endfunction
 endclass
 typedef C#(int,2) Two;
endpackage
module top;
 import p::*;
 typedef C#(int,2) Again;
 int x;
 initial begin
  x=p::C#(int,2)::add(3);
  $display("TRACE param %0d %0d %0d %0d",x,p::Two::count,Again::count,C#(bit[7:0],2)::count);
  x=Again::add();
  $display("TRACE default %0d %0d %0d",C::count,C#()::count,Two::count);
  #1;$finish;
 end
endmodule
