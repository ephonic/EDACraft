module unit_test #(parameter W=8)(output int result);
 class C;
  parameter int N=W+1;
  localparam int M=N+2;
  bit[M-1:0] data;
  function int get();return N+M+$bits(data);endfunction
 endclass
 C c;
 initial begin c=new;result=c.get();end
endmodule
module top;
 int a,b,observed;unit_test#(8) x(a);unit_test#(129) y(b);
 initial begin #1;observed=a+b;if(a!=31||b!=394)$fatal(1,"module class clones");$display("TRACE body clones %0d %0d %0d",a,b,observed);end
endmodule
