`timescale 1ns/1ps
package data;
 typedef struct packed{logic[7:0] a;logic[3:0] b;} item_t;
 item_t record;
 logic[7:0] cells[0:1][2:3];
 bit[7:0] two=0;
 integer unused;
 function automatic integer total();return cells[0][2]+cells[1][3];endfunction
 task automatic update(input integer n);cells[0][2]=n;record.a=n;record.b=4'ha;endtask
endpackage
package other;
 integer unused=40;
endpackage
module top;
 import data::*;
 integer i=0,j=2;reg[7:0] observed=0;
 always @* observed=data::cells[i][j];
 initial begin
  data::update(8'h12);data::cells[1][3]=8'h34;#1;
  if(observed!==8'h12||record.a!==8'h12||record.b!==4'ha||data::total()!==70)$fatal(1,"FAIL package array");
  if(unused!==32'hxxxxxxxx||other::unused!==40)$fatal(1,"FAIL package default");
  two=8'hxx;if(two!==0)$fatal(1,"FAIL package 2state");
  $display("TRACE package array %h %h %0d",observed,record.a,data::total());
  #1;i=1;j=3;#1;if(observed!==8'h34)$fatal(1,"FAIL package sensitivity");
  $display("TRACE package indexed %h",observed);#1;$finish;
 end
endmodule
