`timescale 1ps/1ps
module top;
 class Base;
  int n=9;
  virtual function int get();return n;endfunction
 endclass
 class Derived extends Base;
  function int get();return n+10;endfunction
 endclass
 class Holder;Derived item;endclass
 Holder h;Base source;Derived d;
 int receiver_calls,source_calls,index_calls,ok,observed;
 typedef enum logic[7:0] {A=2,B=8'hfc} T;
 T values[2];
 function automatic Holder receiver();receiver_calls++;return h;endfunction
 function automatic Base actual();source_calls++;return source;endfunction
 function automatic int index();index_calls++;return 1;endfunction
 function automatic int convert(ref Derived dst,input Base src);return $cast(dst,src);endfunction
 initial begin
  h=new;d=new;source=d;values[0]=A;values[1]=A;
  ok=$cast(receiver().item,actual());observed=h.item.get();
  $display("TRACE field %0d %0d %0d %0d",ok,observed,receiver_calls,source_calls);
  source=new;ok=$cast(receiver().item,actual());
  $display("TRACE unchanged %0d %0d %0d %0d",ok,h.item==d,receiver_calls,source_calls);
  ok=$cast(values[index()],8'hfc);
  $display("TRACE element %0d %0h %0d",ok,values[1],index_calls);
  ok=$cast(values[index()],32'h1fc);
  $display("TRACE elementfail %0d %0h %0d",ok,values[1],index_calls);
  source=d;d=null;ok=convert(d,source);
  $display("TRACE ref %0d %0d",ok,d.get());
  if(0 && $cast(d,actual())) $fatal(1,"short circuit");
  $display("TRACE skipped %0d",source_calls);
  $cast(h.item,source);void'($cast(h.item,null));
  $display("TRACE task %0d",h.item==null);
  #1;$finish;
 end
endmodule
