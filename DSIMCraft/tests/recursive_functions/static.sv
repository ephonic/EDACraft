`timescale 1ps/1ps
module top;
 int calls;
 function automatic int outer(int n);
  int saved=n;
  if(n==0)return 1;
  return inner(n-1)+saved;
 endfunction
 function int inner(int n);
  int counter=10;
  automatic int saved=n;
  counter++;calls++;
  if(n==0)return counter;
  return outer(n-1)+saved;
 endfunction
 function int direct(int n);
  if(n==0)return 1;
  return direct(n-1)+n;
 endfunction
 int x,y,z;
 initial begin
  x=outer(4);y=inner(4);z=direct(5);
  $display("TRACE static cycle %0d %0d %0d %0d",x,y,z,calls);
  if(x!=11||y!=25||z!=1||calls!=5)$fatal(1,"static lifetime cycle");
  #2 $finish;
 end
endmodule
