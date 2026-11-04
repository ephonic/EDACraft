class Base; int value;endclass
class Child extends Base;endclass
module top;
 bit observed=0;
 Base a[$],b[$];Child c;Base x;
 initial begin
  observed=1;
  x=new;c=new;a.push_back(x);b.push_back(x);
  $display("TRACE identity %b %b",a===b,a!=b);
  a.push_back(null);b.push_back(null);
  $display("TRACE null %b %b",a===b,a!==b);
  b[0]=c;$display("TRACE distinct %b %b",a==b,a!==b);
 end
endmodule
