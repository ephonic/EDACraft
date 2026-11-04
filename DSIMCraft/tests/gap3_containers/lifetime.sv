`timescale 1ps/1ps
module top;
 task automatic use_map(input int n,output int result);
  int entries[int unsigned];int q[$];int unsigned key;
  entries[0]=n;entries[-1]=n+1;q='{n,n+1};
  #2;
  if(!entries.last(key)||key!=32'hffffffff||entries[key]!=n+1||q[$]!=n+1)$fatal(1,"automatic storage");
  entries[-1]=n+2;q[$]=entries[-1];result=q[$];
 endtask
 int x,y,observed;
 initial begin
  fork use_map(3,x);use_map(7,y);join
  if(x!=5||y!=9)$fatal(1,"automatic fork isolation");observed=x+y;
  use_map(11,x);if(x!=13)$fatal(1,"reused activation");
  $display("TRACE lifetime %0d %0d",observed,x);$finish;
 end
endmodule
