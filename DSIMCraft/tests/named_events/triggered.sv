`timescale 1ns/1ps
module top;
 event e,early;integer instant,changes,rises,falls,sticky,late,never,combined,expired;
 initial begin instant=0;repeat(3)begin @e;instant++;end end
 initial begin changes=0;repeat(3)begin @(e.triggered);changes++;end end
 initial begin rises=0;repeat(3)begin @(posedge e.triggered);rises++;end end
 initial begin falls=0;@(negedge e.triggered);falls++;end
 initial begin sticky=0;#1;#0;wait(e.triggered);sticky=$time;end
 initial begin never=0;#1;#0;wait(!e.triggered);never=1;end
 initial begin combined=0;wait(e.triggered||early.triggered);combined=1;end
 initial begin late=0;#1;->early;@early;late=1;end
 initial begin expired=9;#1;->e;#0;->e;#1;->e;#1;expired=e.triggered;
   if(instant!==3||changes!==1||rises!==1||falls!==0||sticky!==1||late!==0||never!==0||combined!==1||expired!==0)$fatal(1,"triggered semantics");
   $display("TRACE triggered %0d %0d %0d %0d %0d %0d %0d %0d %0d",instant,changes,rises,falls,sticky,late,never,combined,expired);$finish;
 end
endmodule
