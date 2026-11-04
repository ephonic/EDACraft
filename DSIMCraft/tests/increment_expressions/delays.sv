`timescale 1ns/1ps
module top;
integer i=10,delay_value=2,q=0,r=0,observed=0,answer=0;
reg tick=0;
task sample(input integer value,output integer result);
 begin #1;result=value++;return;end
endtask
initial begin
 #1;q<=#(delay_value++)i++;
 r=#2 i++;
 @(posedge tick)observed=++i;
 sample(i++,answer);
 $display("TRACE sampled %0d %0d %0d %0d %0d %0d",q,r,observed,i,delay_value,answer);
 #1;q<=i--;r<=--i;
 #1;$display("TRACE nba %0d %0d %0d",q,r,i);
 q<=#2 i++;
 #3;$display("TRACE delayed %0d %0d",q,i);$finish;
end
initial begin #5;tick=1;end
endmodule
