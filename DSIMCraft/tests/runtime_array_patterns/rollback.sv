module top;
 int q[$]='{1},a[];int observed=0;
 initial begin
  #1;q='{2,3};a='{4};observed=q[0]+a[0];
  #1;q={};a='{};observed=9;
  #1;q='{7};observed=q[0];
  #1;$display("TRACE rollback %0d %0d %0d",observed,q.size(),a.size());$finish;
 end
endmodule
