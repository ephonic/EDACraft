module top;
 class C;
  static int total=3;
  static function int locals(int n);int tmp;static int calls=0;tmp=n;calls++;return tmp+calls*10;endfunction
  static task delayed(int n, output int result);int tmp;tmp=n;#2;total+=tmp;result=tmp;endtask
 endclass
 int a,b,v,observed;
 initial begin
  v=C::locals(2);$display("TRACE local1 %0d",v);
  v=C::locals(5);$display("TRACE local2 %0d",v);
  fork
   C::delayed(7,a);
   begin #1;C::delayed(11,b);end
  join
  observed=C::total;$display("TRACE overlap %0d %0d %0d",a,b,observed);
  #1;$finish;
 end
endmodule
