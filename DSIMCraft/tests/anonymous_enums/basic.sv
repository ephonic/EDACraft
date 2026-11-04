module top;
 enum logic[2:0] {RED=1,GREEN=3,BLUE=5} a=GREEN,b=a,arr[2],q[$];
 int observed;
 initial begin
  if(a!==GREEN||b!==GREEN||a.name()!="GREEN"||a.num()!=3||arr[0]!==3'bxxx)$fatal(1,"defaults/labels");
  a=a.next();b=a.prev();arr[0]=a;arr[1]=b;q.push_back(RED);q.push_back(arr[0]);
  observed=arr[0]+arr[1]+q[0];
  if(observed!=9||q[1].name()!="BLUE")$fatal(1,"identity/containers");
  #1;$display("TRACE basic %s %s %s %0d",a.name(),b.name(),q[1].name(),observed);$finish;
 end
endmodule
