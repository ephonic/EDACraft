module top;
 class C;
  static int count=2;
  static function int setup();count+=3;return count;endfunction
  static int v=setup();
  static C singleton=new;
  int own;
  function new();own=count;count++;endfunction
 endclass
 C a;
 initial begin
  $display("TRACE startup %0d %0d %0d",C::v,C::count,C::singleton.own);
  a=new;
  $display("TRACE startup2 %0d %0d",C::count,a.own);
  #1;$finish;
 end
endmodule
