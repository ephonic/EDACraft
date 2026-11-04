`timescale 1ns/1ps
module top;
integer sum=0,done=0;
task automatic launch();
 logic data[1:3];
 foreach(data[i]) fork begin #1;sum+=i;done++;end join_none
endtask
initial begin
 launch();
 wait fork;
 $display("TRACE escape %0d %0d",sum,done);
 if(sum!=12||done!=3)$fatal(1,"foreach lifetime or terminal index");
end
endmodule
