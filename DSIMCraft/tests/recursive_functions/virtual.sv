`timescale 1ps/1ps
module top;
 class Base;
  int bias;
  virtual function int left(int n);
   if(n==0)return bias;
   return right(n-1)+bias;
  endfunction
  virtual function int right(int n);
   if(n==0)return bias;
   return left(n-1)+bias;
  endfunction
 endclass
 class Derived extends Base;
  function int right(int n);
   if(n==0)return bias+10;
   return left(n-1)+bias+10;
  endfunction
 endclass
 Base b;Derived d;int observed;
 initial begin
  d=new;d.bias=3;b=d;
  observed=b.left(4);
  if(observed!=35||b.right(4)!=45)$fatal(1,"virtual mutual recursion");
  #2 $display("TRACE virtual mutual recursion pass");$finish;
 end
endmodule
