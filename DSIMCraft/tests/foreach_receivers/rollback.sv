`timescale 1ps/1ps
module top;
 class Map;
  int values[int];
  function int total();
   int sum=0;
   foreach(this.values[key])sum+=this.values[key];
   return sum;
  endfunction
 endclass
 Map c;
 int observed;
 initial begin
  c=new;c.values[1]=1;observed=c.total();
  #2;c.values[2]=2;observed=c.total();
  #1;c.values[3]=6;observed=c.total();
  #2;if(observed!=9)$fatal(1,"restored foreach receiver");
  $display("TRACE foreach receivers rollback=%0d",observed);$finish;
 end
endmodule
