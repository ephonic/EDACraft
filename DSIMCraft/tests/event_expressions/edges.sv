`timescale 1ns/1ps
module top;
 logic[3:0]v;logic clk,enable;integer changes,rises,falls,gated;
 initial begin v=0;clk=0;enable=0;changes=0;rises=0;falls=0;gated=0;end
 initial begin #0;forever begin @({v});changes++;end end
 initial begin #0;forever begin @(posedge ({v}));rises++;end end
 initial begin #0;forever begin @(negedge ({v}));falls++;end end
 initial begin #0;forever begin @(posedge (clk&&enable));gated++;end end
 initial begin #1;v=8;enable=1;#1;v[0]=1;clk=1;#1;v[0]=1'bx;enable=0;
 #1;v[0]=1'bz;clk=0;#1;v[0]=1;enable=1;#1;v[0]=0;clk=1;
 #1;v[0]=1'bz;clk=0;#1;v[0]=0;enable=0;#1;
 if(changes!==8||rises!==3||falls!==3||gated!==2)$fatal(1,"four state expression edges");
 $display("TRACE edges %0d %0d %0d %0d",changes,rises,falls,gated);$finish;end
endmodule
