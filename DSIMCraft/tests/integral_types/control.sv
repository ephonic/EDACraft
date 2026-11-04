`timescale 1ns/1ps
module top;
time ticks=2;reg signed[63:0] duration=-1;
integer unsigned total=0;
integer signed final_count=0;
initial begin:run
 for(integer unsigned i=0;i<3;i++)begin #1;total+=i;end
 for(time j=64'h100000000;j<64'h100000003;j++)begin #1;ticks=j;end
 for(integer signed k=-2;k<1;k++)begin #1;final_count+=k;end
 #(ticks[1:0]);total+=10;
 #(ticks[1:0]);$display("TRACE loops %0d %0d %h",total,final_count,ticks);$finish;
end
endmodule
