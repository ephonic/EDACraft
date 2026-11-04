module top;
 int a[int unsigned], b[int signed], copied[int unsigned];
 int unsigned k,indices[$];int signed sk;int sum;int observed;
 initial begin
  a[-1]=9;a[0]=1;a[32'h80000000]=4;a[1]=2;
  a[64'h100000001]=3;
  if(a.num()!=4||a[1]!=3||!a.exists(-1))$fatal(1,"key narrowing");
  if(!a.first(k)||k!=0||!a.next(k)||k!=1||!a.next(k)||k!=32'h80000000||!a.next(k)||k!=32'hffffffff)$fatal(1,"unsigned cursor order");
  if(a.next(k)||k!=32'hffffffff||!a.prev(k)||k!=32'h80000000)$fatal(1,"cursor end/prev");
  if(!a.last(k)||k!=32'hffffffff)$fatal(1,"last");
  foreach(a[i])begin
   if(i<0)$fatal(1,"foreach index must be unsigned");
   sum+=a[i];
  end
  b[-1]=9;b[0]=1;b[32'h80000000]=4;
  if(!b.first(sk)||sk!=32'sh80000000||!b.next(sk)||sk!=-1||!b.next(sk)||sk!=0)$fatal(1,"signed ordering");
  indices=a.find_index with(item>3);
  if(indices.size()!=2||indices[0]!=32'h80000000||indices[$]!=32'hffffffff)$fatal(1,"unsigned locator indices");
  copied=a;a.delete(-1);
  if(a.num()!=3||copied.num()!=4||copied[32'hffffffff]!=9)$fatal(1,"copy independence");
  observed=sum;#1;$display("TRACE unsigned %0d %0d",observed,copied.num());$finish;
 end
endmodule
