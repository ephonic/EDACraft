class Base;int x;function new(int n=0);x=n;endfunction endclass
class Child extends Base;function new(int n=0);super.new(n);endfunction endclass
module top;
 Base a,b,r; Child c;logic cond;int calls;
 function automatic Base effect(Base v);calls++;return v;endfunction
 initial begin
  a=new(3);b=new(7);c=new(9);calls=0;
  cond=1;r=cond?effect(a):effect(b);$display("TRACE one %0d %0d",r.x,calls);
  cond=0;r=cond?effect(a):null;$display("TRACE null %0d %0d",r==null,calls);
  r=cond?a:c;$display("TRACE subtype %0d",r.x);
  cond=1'bx;r=cond?a:b;$display("TRACE unknown %0d %0d %0d",r==null,r==a,r==b);
  r=cond?effect(a):effect(b);$display("TRACE unknown_effect %0d %0d %0d",r==a,r==b,calls);
  r=cond?a:a;$display("TRACE same %0d",r==a);
 end
endmodule
