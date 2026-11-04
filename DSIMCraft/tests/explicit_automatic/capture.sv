`timescale 1ns/1ps
module top;
integer i=0,q=0,done=0;
initial begin
 for(i=1;i<=4;i++)fork
  automatic integer saved=i;
  begin #1;q+=saved;done++;end
 join_none
 wait fork;
 $display("TRACE capture %0d %0d",q,done);
 if(q!=10||done!=4)$fatal(1,"fork declaration capture");
end
endmodule
