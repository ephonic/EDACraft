module top;
 class C;
  static int x=2;
  static string text="abc";
  static int aa[string];
  static int q[$];
  static task put(int v);#1;x=v;endtask
  static function int get();return x;endfunction
 endclass
 C c;int calls,result;
 function automatic void bump(ref int x);x++;endfunction
 function automatic C pick();calls++;return null;endfunction
 initial begin
  result=pick().get();
  $display("TRACE call %0d %0d",calls,result);
  result=pick().x;
  $display("TRACE read %0d %0d",calls,result);
  pick().x=7;
  $display("TRACE write %0d %0d",calls,C::x);
  result=pick().x++;
  $display("TRACE update %0d %0d %0d",calls,result,C::x);
  pick().aa["key"]=11;pick().aa["key"]+=2;result=pick().aa["key"];
  $display("TRACE element %0d %0d",calls,result);
  pick().q.push_back(15);result=pick().q.pop_front();
  $display("TRACE queue %0d %0d",calls,result);
  pick().put(23);
  $display("TRACE task %0d %0d",calls,C::x);
  bump(pick().x);
  $display("TRACE ref %0d %0d",calls,C::x);
  pick().text.putc(1,88);
  $display("TRACE reftext %0d %0d %s",calls,C::x,C::text);
  #1;$finish;
 end
endmodule
