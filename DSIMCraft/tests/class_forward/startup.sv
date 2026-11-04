`timescale 1ps/1ps
module top;
 typedef class Child;
 class Owner;
  Child value;
  function new(int n);
   value=new(n);
  endfunction
 endclass
 class Child;
  int n;
  function new(int value);n=value;endfunction
  function int add(ref int value);value+=n;return value;endfunction
 endclass
 Owner a=new(5),b=new(11);
 int total=7,observed;
 initial begin
  observed=a.value.add(total);observed=b.value.add(total);
  #1;$display("TRACE startup %0d %0d %0d %0d",a.value.n,b.value.n,total,observed);
 end
endmodule
