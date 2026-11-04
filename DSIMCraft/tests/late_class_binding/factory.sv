class Factory #(type T=int);
 static int allocations=0;
 static Factory#(T) cached=get();
 int value=41;
 function new();allocations++;endfunction
 static function Factory#(T) get();if(cached==null)cached=new();return cached;endfunction
endclass
module top;
 Factory#(bit[47:0]) a,b;int stage=0;
 initial begin
  a=Factory#(bit[47:0])::get();b=Factory#(bit[47:0])::get();stage++;#1;
  $display("TRACE factory %0d %0d %0d",a==b,a.value,Factory#(bit[47:0])::allocations);$finish;
 end
endmodule
