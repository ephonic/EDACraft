`timescale 1ns/1ps
package header_counter;
 parameter integer GAP=1;
 integer total=0;
 function automatic integer read_total();return total;endfunction
 task automatic add(input integer amount);total=total+amount;endtask
endpackage
module worker import header_counter::GAP; import header_counter::total,header_counter::add;
 #(parameter integer ID=GAP);
 initial begin #(ID);add(ID);#(GAP);total<=total+8;end
endmodule
module top import header_counter::*; ;
 worker #(1) a();worker #(4) b();
 integer observed=0;
 initial begin #3;observed=read_total();if(observed!=9)$fatal(1,"first shared package update");
 #3;observed=read_total();if(observed!=21||total!=21)$fatal(1,"header package identity");
 $display("TRACE header shared %0d %0d",observed,total);end
endmodule
