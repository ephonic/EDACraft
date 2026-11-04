`timescale 1ns/1ps
module top;
 logic[7:0] a,b;logic[129:0]wide;
 integer sums,xors,joined,equal_changes,wide_changes,wide_rises;
 initial begin a=0;b=0;wide=0;sums=0;xors=0;joined=0;equal_changes=0;wide_changes=0;wide_rises=0;end
 initial begin #0;forever begin @(a+b);sums++;end end
 initial begin #0;forever begin @(a^b);xors++;end end
 initial begin #0;forever begin @({a,b});joined++;end end
 initial begin #0;forever begin @(a==b);equal_changes++;end end
 initial begin #0;forever begin @(wide^130'd1);wide_changes++;end end
 initial begin #0;forever begin @(posedge (|wide));wide_rises++;end end
 initial begin #1;a=1;b=1;wide[129]=1;#1;a=2;b=0;wide[70]=1;
 #1;a=3;#1;a=0;wide=0;#1;
 if(sums!==3||xors!==3||joined!==4||equal_changes!==2||wide_changes!==3||wide_rises!==1)$fatal(1,"expression changes");
 $display("TRACE expressions %0d %0d %0d %0d %0d %0d",sums,xors,joined,equal_changes,wide_changes,wide_rises);$finish;end
endmodule
