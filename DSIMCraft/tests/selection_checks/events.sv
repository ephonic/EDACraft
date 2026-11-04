`timescale 1ns/1ps
module top;
logic pulse=0,guard=0;integer q=0,r=0,k;
initial forever begin
 @(pulse);
 unique if(guard)q=1; // flushed after second event in same time slot
end
initial begin #1;pulse=1;#0;guard=1;pulse=0;end
initial begin
 #2;guard=0;
 for(k=0;k<3;k++)begin
  unique if(guard)r=1; // report no-match 2000 count=3
 end
 #0;guard=1; // a delay resume does not flush the report queue
 #1;if(q!==1||r!==0)$fatal(1,"event resume and delay");
 $display("TRACE events %0d %0d",q,r);
end
endmodule
