module top;
 typedef int values_t[$];
 values_t q='{1,2,3},r;int a[];int observed;
 function automatic values_t get(input bit present);if(present)return '{4,5};return {};endfunction
 initial begin
  if(q.size()!=3||q[0]!=1||q[2]!=3)$fatal(1,"initializer");
  r=get(1);a='{7,7,9};if(r.size()!=2||a.size()!=3||a[2]!=9)$fatal(1,"returned values");
  q=r;r=get(0);if(r.size()!=0||q.size()!=2)$fatal(1,"empty result and copy");
  observed=q[0]+q[1]+a[0];q={};
  a={{8'h1,8'h2},3};if(a.size()!=2||a[0]!=258||a[1]!=3)$fatal(1,"nested packed concatenation");a='{};
  if(q.size()!=0||a.size()!=0||observed!=16)$fatal(1,"empty assignment");
  #1;$display("TRACE queue %0d",observed);$finish;
 end
endmodule
