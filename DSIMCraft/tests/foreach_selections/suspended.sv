`timescale 1ps/1ps
module top;
 class Cell;int values[int];endclass
 Cell nodes[2];
 int choice,calls,observed;
 function automatic int pick();calls++;return choice;endfunction
 initial begin
  nodes[0]=new;nodes[1]=new;
  nodes[0].values[0]=1;nodes[0].values[2]=1;
  nodes[1].values[5]=1;nodes[1].values[9]=1;
  choice=0;calls=0;observed=0;
  foreach(nodes[pick()].values[k])begin
   #1;observed+=k;choice=1;
  end
  if(observed!=14 || calls!=4 || $time!=3)$fatal(1,"suspended receiver changed");
  $display("TRACE foreach suspended observed=%0d calls=%0d",observed,calls);$finish;
 end
endmodule
