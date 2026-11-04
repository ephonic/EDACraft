`timescale 1ns/1ps
module top;
integer sum=0,done=0,k=0;
task automatic launch(input integer tag);
 logic values[2:1][1:3];
 logic skipped[2:1][1:3];
 logic [3:1] descending;
 logic singleton[7:7];
 foreach(values[i,j]) fork begin #2;sum+=tag*100+i*10+j;done++;end join_none
 foreach(skipped[,j]) fork begin #3;sum+=j;done++;end join_none
 foreach(singleton[i]) fork begin #3;sum+=i;done++;end join_none
 foreach(values[i,]) fork begin #3;sum+=i;done++;end join_none
 foreach(descending[i]) fork begin #4;sum+=i;done++;end join_none
endtask
initial begin
 for(k=1;k<=3;k++)launch(k);
 #1;
 if(sum!=0||done!=0)$fatal(1,"early child delivery");
 wait fork;
 $display("TRACE multi %0d %0d",sum,done);
 if(sum!=3726||done!=45)$fatal(1,"escaped multidimensional loop frames");
end
endmodule
