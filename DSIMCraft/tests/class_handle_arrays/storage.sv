module top;
 class Base;
  int value;
  virtual function int kind();return 1;endfunction
 endclass
 class Derived extends Base;
  virtual function int kind();return 2;endfunction
 endclass
 class Store;
  Base items[];
  function new();items=new[2];endfunction
 endclass
 Store a,b;Base copied[];Derived d;Base x;int observed;
 initial begin
  a=new;b=new;
  if(a.items.size()!=2||a.items[0]!=null||a.items[-1]!=null)$fatal(1,"null defaults");
  d=new;d.value=17;x=new;x.value=23;
  a.items[0]=d;a.items[1]=x;a.items[2]=d;
  if(a.items.size()!=2||a.items[0].kind()!=2||a.items[1].kind()!=1)$fatal(1,"typed elements");
  a.items=new[4](a.items);
  if(a.items[2]!=null||a.items[3]!=null||a.items[0]!=d)$fatal(1,"resize retains references");
  b.items=a.items;b.items[0].value=19;
  if(a.items[0].value!=19)$fatal(1,"pointee identity");
  b.items[0]=null;
  if(a.items[0]!=d)$fatal(1,"array copy isolation");
  copied=a.items;copied[1]=null;
  if(a.items[1]!=x)$fatal(1,"ordinary array isolation");
  a.items={x,d,null};
  foreach(a.items[i])if(a.items[i]!=null)observed+=a.items[i].value;
  if(observed!=42)$fatal(1,"handle foreach");
  a.items.delete();if(a.items.size()!=0||b.items.size()!=4||copied.size()!=4)$fatal(1,"delete isolation");
  $display("TRACE class handle dynamic null resize copy identity dispatch pass");$finish;
 end
endmodule
