module top;
 class Callback;
  int value;
  Callback link;
  function new(int n);value=n;endfunction
  virtual function int decode();return value;endfunction
 endclass
 class Doubled extends Callback;
  function new(int n);super.new(n);endfunction
  function int decode();return value*2;endfunction
 endclass
 class Iterator;
  Callback head;
  function Callback last();return head;endfunction
  function Callback prev(Callback current);return current.link;endfunction
 endclass
 Iterator iter=new;
 Callback a=new(3),tail=new(7),cb=new(99);
 Doubled b=new(5);
 int observed,calls;
 function Callback first();calls++;return iter.last();endfunction
 initial begin
  a.link=b;b.link=tail;iter.head=a;
  for(Callback cb=first(),saved=cb;cb!=null;cb=iter.prev(cb))begin
   if(saved!=a)$fatal(1,"initializer binding/order");
   observed+=cb.decode();
  end
  if(observed!=20 || calls!=1 || cb.value!=99)$fatal(1,"callback scope");
  for(Callback cb=iter.last();cb!=null;cb=iter.prev(cb))begin
   if(cb==b)continue;
   observed+=cb.decode();
   if(cb==tail)break;
  end
  if(observed!=30)$fatal(1,"callback control");
  $display("TRACE callbacks %0d %0d %0d",observed,calls,cb.value);
 end
endmodule
