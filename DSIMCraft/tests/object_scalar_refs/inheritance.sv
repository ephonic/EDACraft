module top;
 class Base;int value=3;endclass
 class Derived extends Base;int value=20;endclass
 Derived derived;Base base;int observed;
 function automatic void add(ref int a,ref int b);a+=4;b+=5;endfunction
 initial begin derived=new;base=derived;add(base.value,derived.value);observed=base.value;
  $display("TRACE inheritance %0d %0d",observed,derived.value);
 end
endmodule
