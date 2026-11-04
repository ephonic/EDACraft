module top;
 class Holder;int values[$];endclass
 Holder h;int q[$],fixed_values[3],observed;
 initial begin
  h=new;h.values='{3,9,7};q='{7,3,9};fixed_values='{9,7,3};
  #2;h.values.rsort;q.rsort;fixed_values.rsort;observed=q[0];
  if(h.values[0]!=9||fixed_values[0]!=9)$fatal(1,"first order");
  #1;h.values.sort;q.sort;fixed_values.sort;observed=q[1];
  if(h.values[1]!=7||fixed_values[1]!=7)$fatal(1,"restored order");
  #2;$display("TRACE ordering rollback %0d",observed);$finish;
 end
endmodule
