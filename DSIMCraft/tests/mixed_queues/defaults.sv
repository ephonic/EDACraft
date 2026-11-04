module top;
 typedef logic[7:0] Q[$];Q a[int];int observed;logic[7:0] value;
 initial begin
  value=a[1].size();if(value!==0||a.num()!=0||a.exists(1))$fatal(1,"size materialized key");
  value=a[2][0];if(value!==8'hxx||a.num()!=0||a.exists(2))$fatal(1,"read materialized key");
  value=a[3].pop_front();if(value!==8'hxx||a.num()!=1||!a.exists(3))$fatal(1,"pop missing key");
  a[4].delete();if(a.num()!=2||!a.exists(4))$fatal(1,"delete missing key");
  a[5].reverse();if(a.num()!=3||!a.exists(5))$fatal(1,"reverse missing key");
  a[6]={};if(a.num()!=4||!a.exists(6))$fatal(1,"empty assignment");
  a[7][2]=3;if(a.num()!=5||!a.exists(7)||a[7].size()!=0)$fatal(1,"invalid write missing key");
  a[7][0]=8;if(a[7].size()!=1||a[7][0]!=8)$fatal(1,"append at size");
  observed=a.num();$display("TRACE mixed defaults %0d",observed);$finish;
 end
endmodule
