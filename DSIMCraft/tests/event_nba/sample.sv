`timescale 1ns/1ps
module top;
event e;logic clk=0,g=0;
logic[129:0]src=130'h200000000000000000000000000000005,q=0;
logic signed[7:0]negative=-3;logic signed[129:0]sq=0;
logic[7:0]unknown=8'b1x01z0x1;bit[7:0]clean=0;
integer calls=0,stage=0;
typedef enum logic[1:0]{IDLE=0,RUN=1}state_t;state_t state=IDLE;
function logic[129:0]capture();calls++;return src;endfunction
initial begin
q<=@(posedge clk iff g)capture();sq<=@e negative;clean<=@(negedge clk)unknown;state<=@e RUN;
stage=1;#1;src=99;negative=5;unknown=0;
#7;$display("TRACE sample %0d %0d %0d %0d %0d %0d",calls,q===130'h200000000000000000000000000000005,sq===-130'sd3,clean,state,stage);
if(calls!==1||q!==130'h200000000000000000000000000000005||sq!==-130'sd3||clean!==145||state!==RUN||stage!==1)$fatal(1,"sample mismatch");$finish;end
initial begin #2 clk=1;#1 clk=0;#1 g=1;clk=1;#1 ->>e;end
endmodule
