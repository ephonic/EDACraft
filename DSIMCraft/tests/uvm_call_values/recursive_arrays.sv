module top;
 function automatic int f(int n);
  int a[];
  if(n==0)return 1;
  a=new[1];a[0]=n;
  return g(n-1,a)+a[0];
 endfunction
 function automatic int g(int n,int a[]);
  if(n==0)return a[0];
  a[0]+=10;return f(n-1)+a[0];
 endfunction
 int result;
 initial begin result=f(3);$display("TRACE array_bridge %0d",result);end
endmodule
