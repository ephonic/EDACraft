`timescale 1ps/1ps
module top;
 class Walker;
  int value;
  function int descend(int n,int amount);
   int previous;
   previous=value;value+=amount;
   if(n==0)return previous;
   return descend(n-1,amount)+previous;
  endfunction
 endclass
 Walker w;int observed,checksum;
 initial begin
  w=new;
  #2 w.value=1;checksum=w.descend(3,2);observed=w.value;
  if(checksum!=16||observed!=9)$fatal(1,"recursive heap writes");
  #1 w.value=3;checksum=w.descend(1,2);observed=w.value;
  if(checksum!=8||observed!=7)$fatal(1,"recursive restored state");
  $display("TRACE recursive checkpoint heap pass");$finish;
 end
endmodule
