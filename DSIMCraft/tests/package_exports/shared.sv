`timescale 1ns/1ps
package storage;
 integer total=0;
 integer cells[0:1];
 function automatic integer bump(integer amount);total=total+amount;return total;endfunction
 task automatic put(input integer index,input integer value);
  #1;cells[index]=value;total=total+value;
 endtask
endpackage
package first;
 import storage::*;
 export storage::total,storage::cells,storage::bump,storage::put;
endpackage
package second;
 import first::*;
 export first::total,first::cells,first::bump,first::put;
endpackage
module child(output integer value);
 import second::*;
 initial begin value=0;#1;value=bump(3);put(1,4);end
endmodule
module top;
 import second::*;
 integer value;
 child u(value);
 initial begin
  cells[0]=1;cells[1]=2;
  #3;if(total!=7||first::total!=7||storage::total!=7||cells[1]!=4||value!=3)$fatal(1,"export storage alias");
  storage::total<=11;
  #1;if(second::total!=11)$fatal(1,"export NBA alias");
  $display("TRACE export shared %0d %0d %0d %0d",total,cells[0],cells[1],value);
 end
endmodule
