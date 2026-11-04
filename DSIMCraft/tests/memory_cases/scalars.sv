`timescale 1ns/1ps
module lane(output wire mirror);
reg a=1;wire b=a;logic c=1;bit d=1;reg memory[2];
assign mirror=b[0];
initial begin
memory[0]=1;memory[1]=0;
$display("TRACE scalar %b %b %b %b %b",a[0],b[0:0],c[0+:1],d[0-:1],memory[0][0:0]);
a[0]=0;memory[1][0]<=1;c[0:0]=1'bx;d[0]=1'bx;
#1;$display("TRACE stores %b %b %b %b %b",a[0:0],memory[1][0],c[0],d[0],mirror);
a[0+:1]<=1'bz;
#1;$display("TRACE scalar-z %b %b",a[0-:1],b[0:0]);
$display("TRACE dimensions %0d",$dimensions(memory));
end
endmodule
module top;wire mirror;lane dut(mirror);endmodule
