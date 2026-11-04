module top;
 int observed;
 function automatic int count(input int n);
  enum {ZERO,ONE,TWO} a=ONE,b=a;
  if(a.name()!="ONE"||b!=ONE)return -1;
  repeat(n)a=a.next();
  return a;
 endfunction
 initial begin observed=count(1)+count(2);if(observed!=2)$fatal(1,"automatic locals");#1;$display("TRACE locals %0d",observed);$finish;end
endmodule
