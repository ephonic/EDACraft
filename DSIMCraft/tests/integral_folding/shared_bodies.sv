module top;
 class Tree;
  static int calls=0; int bias;
  function new(int n);bias=n;endfunction
  function int f0(int n);calls++;return n+bias;endfunction
  function int f1(int n);return f0(n)+f0(n+1);endfunction
  function int f2(int n);return f1(n)+f1(n+1);endfunction
  function int f3(int n);return f2(n)+f2(n+1);endfunction
  function int f4(int n);return f3(n)+f3(n+1);endfunction
 endclass
 Tree a,b;int first,second;
 initial begin
  a=new(1);b=new(3);first=a.f4(2);second=b.f4(3);
  if(first!=80||second!=128||Tree::calls!=32)$fatal(1,"shared bodies must preserve activations");
  $display("TRACE shared %0d %0d %0d",first,second,Tree::calls);$finish;
 end
endmodule
