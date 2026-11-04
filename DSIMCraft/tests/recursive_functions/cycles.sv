`timescale 1ps/1ps
module top;
  function automatic integer a(input integer n); if(n==0) return 1; return b(n-1)+n; endfunction
  function automatic integer b(input integer n); if(n==0) return 2; if(n==3) return b(n-1)+a(n-2); return a(n-1)+n; endfunction
  integer x,y;
  initial begin x=a(6); y=b(6); if(x!=23||y!=23)$fatal(1,"multiple recursion captures"); #2 $display("TRACE %0d %0d",x,y);$finish; end
endmodule
