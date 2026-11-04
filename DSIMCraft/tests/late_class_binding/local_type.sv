class Utility #(type T=int);
 static int calls=7;
 static function int value();calls++;return $bits(T)+calls;endfunction
endclass
class Client;
 function int value();
  typedef struct packed {bit[47:0] bits;} local_t;
  return Utility#(local_t)::value();
 endfunction
endclass
module top;
 Client c;int stage=0;
 initial begin c=new();$display("TRACE local %0d",c.value());stage++;#1;$display("TRACE again %0d",c.value());$finish;end
endmodule
