module top;
 class C;string q[$];endclass
 C a;string q[$],backup[$],s;int observed;
 initial begin
  a=new();q.push_back("before");a.q.push_back("object-before");backup=q;
  #2;
  q[0]="after";a.q[0]="object-after";q.push_back("tail");a.q.push_back("object-tail");
  observed=9;
  #1;
  s=q.pop_front();if(s!="after"||a.q.pop_front()!="object-after"||backup[0]!="before")$fatal(1,"restore strings");
  observed=7;
  #2;
  $display("TRACE rollback %s %s %0d",q[0],a.q[0],observed);$finish;
 end
endmodule
