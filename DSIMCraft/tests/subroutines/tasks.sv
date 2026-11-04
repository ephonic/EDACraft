`timescale 1ns/1ps
module top;
integer arg=7,answer=-1,counter=0,index=0;
reg signed [79:0] data=-80'sd3;
reg [15:0] words[0:1];
reg event_signal=0;
task bump(input integer a,output integer b,inout signed [79:0] v);
 integer local_count=0;
 begin
  local_count++;
  #2;
  v=v+a;
  b=a*2+local_count;
 end
endtask
task legacy;
 input [15:0] a;
 output [15:0] b;
 begin #1;b=a+16'h10;end
endtask
task wait_event(output integer b);
 begin @(posedge event_signal);b=counter+20;end
endtask
task tick;
 begin #1;counter++;end
endtask
initial begin
 words[0]=0;words[1]=0;
 bump(arg,answer,data);
 $display("TRACE task %0d %h",answer,data);
 arg=4;bump(arg,answer,data);
 $display("TRACE task %0d %h",answer,data);
 legacy(16'hffff,words[index]);
 tick();$display("TRACE legacy %h %h %0d",words[0],words[1],counter);
 wait_event(answer);$display("TRACE event %0d",answer);
 #3;$finish;
end
initial begin #1;arg=99;#3;index=1;#4;counter=5;event_signal=1;end
endmodule
