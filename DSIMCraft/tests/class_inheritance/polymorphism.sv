`timescale 1ps/1ps
module top;
class Base;
 int id;
 function new(int n=2);id=n;endfunction
 virtual function int value(int n=3);return id+n;endfunction
 function int fixed_value();return id;endfunction
 function int nested();return value(1);endfunction
 virtual function string text();return "base";endfunction
endclass
class Derived extends Base;
 int extra;
 function new(int n,int e);super.new(n);extra=e;endfunction
 function int value(int renamed=9);return super.value(renamed)+extra;endfunction
 function int fixed_value();return id+extra;endfunction
 function string text();return "derived";endfunction
endclass
class Leaf extends Derived;
 function new();super.new(6,10);endfunction
 function int value(int n=20);return super.value(n)+100;endfunction
endclass
Base b;Derived d;Leaf l;int calls;int observed;
function automatic Base choose();calls++;return b;endfunction
function automatic int next_arg();calls++;return 4;endfunction
function automatic Base identity(Base p);return p;endfunction
initial begin
 b=new;d=new(5,7);l=new;
 $display("TRACE base=%0d derived=%0d leaf=%0d",b.value(),d.value(),l.value());
 b=d;observed=b.value();
 observed=b.value(.n(3));
 $display("TRACE alias=%0d nested=%0d fixed=%0d/%0d text=%s eq=%0d",observed,b.nested(),b.fixed_value(),d.fixed_value(),b.text(),b==d);
 b=l;observed=choose().value(next_arg());
 $display("TRACE leaf=%0d nested=%0d calls=%0d identity=%0d",observed,b.nested(),calls,identity(d)==d);
 #2;$finish;
end
endmodule
