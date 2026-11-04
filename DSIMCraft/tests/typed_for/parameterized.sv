module top;
 class Box#(type T=int);
  T value;
  function new(T n);value=n;endfunction
 endclass
 class Worker#(type T=int,parameter int N=3);
  function T total();
   T sum=0;
   for(Box#(T) first=new(1),second=first;first.value<=N;first.value++)begin
    if(first!=second)return '1;
    for(T i=0;i<first.value;i++)sum+=first.value;
   end
   return sum;
  endfunction
 endclass
 Worker#(logic[68:0],3) a=new;
 Worker#(int,4) b=new;
 logic[68:0] observed;
 int other;
 initial begin
  observed=a.total();other=b.total();
  if(observed!=14 || other!=30 || a.total()!=14)$fatal(1,"specialized loop binding");
  $display("TRACE parameterized %0d %0d",observed,other);
 end
endmodule
