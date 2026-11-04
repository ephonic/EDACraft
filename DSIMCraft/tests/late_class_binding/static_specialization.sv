class Utility #(type T=int);
  static int calls=7;
  static function int value(); calls++; return $bits(T)+calls; endfunction
endclass
class Client #(type T=int);
  static function int value(); return Utility#(T)::value(); endfunction
endclass
module top;
 int stage=0;
 initial begin
  $display("TRACE late %0d",Client#(bit[47:0])::value()); stage++; #1;
  $display("TRACE reused %0d",Client#(bit[47:0])::value()); stage++; #1;
  $display("TRACE other %0d",Client#(bit[15:0])::value()); $finish;
 end
endmodule
