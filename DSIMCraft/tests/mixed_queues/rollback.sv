module top;
 class Holder;typedef int Q[$];Q values[int];endclass
 typedef int Q[$];Q a[int],copy[int];Holder h;int observed;
 initial begin
  h=new;a[1]='{7,3,9};h.values[2]='{3,9,7};
  #2;a[1].rsort;copy=a;h.values[2].rsort;observed=a[1][0];
  if(copy[1][0]!=9||h.values[2][0]!=9)$fatal(1,"before rollback");
  #1;a[1].sort;h.values[2].sort;observed=a[1][1];a.delete(1);
  if(a.num()!=0||copy[1][0]!=9||h.values[2][1]!=7)$fatal(1,"after rollback");
  #2;$display("TRACE mixed rollback %0d",observed);$finish;
 end
endmodule
