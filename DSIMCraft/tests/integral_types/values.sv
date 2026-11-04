`timescale 1ns/1ps
module top;
integer signed si=-1;
integer unsigned ui=32'hffffffff;
time stamp=64'hffffffffffffffff;
reg signed[63:0] st=-3;
time ut=64'h8000000000000000;
reg[79:0]wide=0;
integer compare=0;
initial begin
 #1;compare=(si<0)*100+(ui<0)*10+(st<0);
 wide=si;$display("TRACE integer %0d %0d %h %0d",si,ui,wide,compare);
 wide=ui;$display("TRACE unsigned %h",wide);
 wide=stamp;$display("TRACE time %0d %h",stamp,wide);
 wide=st;$display("TRACE signed %0d %h",st,wide);
 st>>>=1;ut>>>=1;ui+=1;stamp++;
 $display("TRACE shift %0d %h %0d %h",st,ut,ui,stamp);
 #1;ui=32'h80000000;si=-7;st=-17;
 $display("TRACE arithmetic %0d %0d %0d %0d",ui/3,si/3,st/3,st%3);
 ui=32'bx001;stamp=64'bz101;
 $display("TRACE four %h %h",ui,stamp);
 #1;$finish;
end
endmodule
