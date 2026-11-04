`timescale 1ns/1ps
module top;
logic[7:0]data=0;logic[129:0]wide=0;integer offset=0;
integer changes=0,rises=0,signed_changes=0;
function automatic logic[7:0] invert(input logic[7:0]x);logic[7:0]tmp;tmp=~x;return tmp;endfunction
function automatic logic odd(input logic[7:0]x);return ^invert(x);endfunction
function automatic logic[129:0] mix(input logic[129:0]x,input logic[7:0]y);
logic[129:0]rows[0:1];rows[0]=x;rows[1]=y;return rows[0]^rows[1];endfunction
function automatic integer plus_one(input integer x);return x+1;endfunction
initial begin #0;forever begin @(mix(wide,data));changes++;end end
initial begin #0;forever begin @(posedge odd(data));rises++;end end
initial begin #0;forever begin @(plus_one(offset));signed_changes++;end end
initial begin
#1 data=1;offset=-1;
#1 data=3;offset=1;
#1 wide[129]=1;
#1 wide=3;
#1 data=3;
#1 data=8'b000000x1;offset=32'h80000000;
#1 data=0;#1 wide=0;
#1 $display("TRACE value %0d %0d %0d",changes,rises,signed_changes);
if(changes!==7||rises!==2||signed_changes!==3)$fatal(1,"value mismatch");$finish;
end
endmodule
