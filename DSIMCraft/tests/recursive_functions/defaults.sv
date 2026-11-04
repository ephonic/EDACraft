`timescale 1ps/1ps
module top;
 class Counter;
  int bias;
  function string text(int n=2,string prefix="x");
   if(n==0)return prefix;
   return text(n-1,{prefix,"y"});
  endfunction
  function int a(int n=3,int k=bias);
   if(n==0)return k;
   return b(n-1,k+1)+k;
  endfunction
  function int b(int n=2,int k=bias);
   if(n==0)return k;
   return a(n-1,k+1)+k;
  endfunction
 endclass
 Counter a,b;int observed;
 initial begin
  a=new;b=new;a.bias=2;b.bias=7;
  if(a.text()!="xyy"||a.a()!=14||b.a()!=34||a.b()!=9||b.b()!=24)$fatal(1,"recursive defaults");
  observed=a.a(2)+b.b(1);
  if(observed!=24)$fatal(1,"recursive cached capture");
  #2 $display("TRACE recursive defaults text pass");$finish;
 end
endmodule
