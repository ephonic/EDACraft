`timescale 1ps/1ps
module top;
class Base;
 logic [128:0] bits=129'h10000000000000000f123456789abcdef0;
 virtual function int sum(input int xs[2],ref int total,output string label);
  total+=xs[0]+xs[1];label="base";return total;
 endfunction
 virtual function [128:0] wide();return bits;endfunction
 virtual function Base me();return this;endfunction
endclass
class Derived extends Base;
 function int sum(input int xs[2],ref int total,output string label);
  total+=xs[0]*xs[1];label="derived";return total;
 endfunction
 function [128:0] wide();return bits ^ 129'h100000000000000000000000000000000;endfunction
 function Derived me();return this;endfunction
endclass
Base b;Derived d;int xs[2];int total=1,result;string label;logic [128:0] observed;
initial begin
 xs[0]=3;xs[1]=4;d=new;b=d;
 result=b.sum(xs,total,label);observed=b.wide();
 $display("TRACE signatures result=%0d total=%0d label=%s wide=%h self=%0d",result,total,label,observed,b.me()==d);
 #2;$finish;
end
endmodule
