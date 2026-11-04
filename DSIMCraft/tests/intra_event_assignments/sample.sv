`timescale 1ns/1ps
module top;
event ready;logic clk=0,g=0,pulse=0;
logic[129:0]src=130'h200000000000000000000000000000005,q=0;
logic signed[7:0]signed_src=-3;logic signed[129:0]signed_q=0;
logic[7:0]unknown=8'b1x01z0x1;bit[7:0]clean=0;
typedef enum logic[1:0]{IDLE=0,RUN=1}state_t;state_t choice=RUN,state=IDLE;
integer calls=0;
function logic[129:0]capture();calls++;return src;endfunction
initial begin
q=@(posedge clk iff g)capture();
signed_q=@ready signed_src;
clean=@(negedge clk)unknown;
state=@(pulse)choice;
#1 $display("TRACE sample %0d %0d %0d %0d %0d",calls,q===130'h200000000000000000000000000000005,signed_q===-130'sd3,clean,state);
if(calls!==1||q!==130'h200000000000000000000000000000005||signed_q!==-130'sd3||clean!==145||state!==RUN)$fatal(1,"sample mismatch");$finish;end
initial begin
#1 src=99;clk=1;
#1 clk=0;
#1 g=1;clk=1;
#1 signed_src=5;
#1 ->>ready;
#1 unknown=0;clk=0;
#1 choice=IDLE;pulse=1;end
endmodule
