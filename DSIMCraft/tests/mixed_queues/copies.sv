module top;
 typedef int Q[$];Q a[int],q;int observed,calls;
 function automatic Q transform(input Q values);values.push_front(7);return values;endfunction
 function automatic int key();calls++;return 4;endfunction
 initial begin
  q='{3,1,5};a[key()]=q;if(calls!=1)$fatal(1,"assignment address");q[0]=90;
  if(a[4][0]!=3)$fatal(1,"leaf copy ownership");
  q=a[4];a[4]={a[4],8};if(q.size()!=3||a[4].size()!=4)$fatal(1,"concatenation");
  q=transform(a[4]);if(q[0]!=7||q.size()!=5||a[4].size()!=4)$fatal(1,"input copy");
  a[6]=q;a[6].delete();if(!a.exists(6)||a[6].size()!=0)$fatal(1,"leaf clear");
  a[4].sort with(-item);q=a[4].find with(item>3);if(q.size()!=2)$fatal(1,"locator");
  if(a[4].sum()!=17||a[4].sum with(item*2)!=34)$fatal(1,"reduction");
  observed=q[0]+q[1];$display("TRACE mixed copies %0d",observed);$finish;
 end
endmodule
