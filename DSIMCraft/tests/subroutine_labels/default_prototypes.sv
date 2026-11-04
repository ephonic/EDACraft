interface values;
 int bias=3;
 modport view(import function int get(input int renamed,input int other=renamed+5));
 function automatic int get(input int a,input int b=a+1);return b+bias;endfunction : get
endinterface
module client(values.view v,output int observed);
 initial observed=v.get(7);
endmodule
module top;
 class C;
  int value;
  extern function new(int a=3,int b=a+2);
  extern function int get(int a,int b=a+4);
 endclass
 function C::new(int a,int b);value=b;endfunction : new
 function int C::get(int a,int b);return value+b;endfunction : get
 values v();wire[31:0] observed;client c(v.view,observed);
 C obj;int direct;
 initial begin obj=new();direct=v.get(7);#1;
  $display("TRACE defaults prototypes %0d %0d %0d",observed,direct,obj.get(10));$finish;
 end
endmodule
