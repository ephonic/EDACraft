module top;
 class Box #(parameter int N=3);
  int v;function new();v=N;endfunction
 endclass
 virtual class Provider;
  typedef int Q[$];
  pure virtual function Q values();
  pure virtual function Box#(3) item();
 endclass
 class Concrete extends Provider;
  virtual function Q values();return {7,11};endfunction
  virtual function Box#(3) item();Box#(3) b;b=new();return b;endfunction
 endclass
 typedef int Values[$];
 Provider provider;Concrete concrete;Values data;Box#(3) box;
 int observed;
 initial begin
  concrete=new();provider=concrete;data=provider.values();box=provider.item();
  observed=data[1]+box.v;$display("TRACE virtual %0d %0d %0d",data.size(),data[1],box.v);#1;$finish;
 end
endmodule
