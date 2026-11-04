`timescale 1ns/1ps
module top;
event a,b,c,x,y,z;
integer done=0,bad=0;
initial wait_order(a,b,c) done=1;else done=-1;
initial wait_order(x,y,z) bad=1;else bad=-1;
initial begin
 #1;->>a;->>b;->>c;->>y;->>x;->>z;
 #1;$display("TRACE nba %0d %0d",done,bad);
 if(done!=1||bad!=-1)$fatal(1,"NBA ordered trigger batch");
end
endmodule
