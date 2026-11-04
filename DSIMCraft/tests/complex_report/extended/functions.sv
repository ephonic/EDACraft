module tb;
  function automatic integer dbl(input integer x); dbl=2*x; endfunction
  function automatic integer sum(input integer n);
    integer i;
    begin sum=0;for(i=0;i<n;i=i+1)sum=sum+i;end
  endfunction
  function automatic integer fact(input integer n);
    if(n<=1)fact=1;else fact=n*fact(n-1);
  endfunction
  function automatic integer fib(input integer n);
    integer a,b;
    begin
      if(n<2)fib=n;
      else begin a=fib(n-1);b=fib(n-2);fib=a+b;end
    end
  endfunction
  localparam integer W=dbl(4),S=sum(8),NEG=dbl(-7);
  reg [W-1:0] v;
  integer a,b;
  initial begin
    v='1;a=fact(7);b=fib(9);
    if(W!=8||S!=28||NEG!=-14||v!==8'hff||a!=5040||b!=34)$fatal(1,"functions mismatch %d %d %d %d %d",W,S,NEG,a,b);
    $display("TRACE functions %0d %0d %0d %0d %0d",W,S,NEG,a,b);
    $finish;
  end
endmodule
