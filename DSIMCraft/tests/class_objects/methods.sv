`timescale 1ps/1ps
module top;
class Counter;
  int value=1;
  function new(int start=2);value=start;endfunction
  function int add(int n);value+=n;return value;endfunction
  function int nested(int n);return add(n)+add(1);endfunction
  function Counter identity();return this;endfunction
  function int other(Counter rhs);return rhs.value+value;endfunction
endclass
Counter a,b,c;
int observed;
function automatic Counter keep(Counter p);return p;endfunction
function automatic void change(ref Counter p,Counter q);p=q;endfunction
initial begin
 a=new(4);b=new(20);c=a.identity();
 $display("TRACE identity=%0d nested=%0d",a==c,a.nested(3));
 c=keep(b);change(a,b);
 $display("TRACE handle=%0d sum=%0d",a==c,b.other(c));
 $display("TRACE increment=%0d",b.value++);
 b.value+=2;
 observed=a.value;
 $display("TRACE final=%0d",a.value);
 $finish;
end
endmodule
