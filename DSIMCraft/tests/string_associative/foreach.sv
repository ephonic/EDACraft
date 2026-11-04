module top;
 int aa[string];int sum,visits;
 class C;
  int counts[string];
  function int total();int n;n=0;foreach(counts[k])n=n+counts[k]+k.len();return n;endfunction
 endclass
 C a;
 initial begin
  aa[""]=3;aa["a"]=5;aa["ab"]=7;
  foreach(aa[k])begin visits=visits+1;sum=sum+aa[k]+k.len();end
  a=new;a.counts=aa;aa.delete();
  foreach(a.counts[k])begin $display("TRACE key <%s> %0d",k,a.counts[k]);end
  $display("TRACE totals %0d %0d %0d %0d",sum,visits,a.total(),aa.size());
  $finish;
 end
endmodule
