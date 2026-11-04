`timescale 1ps/1ps
module CELL(input C,D,E,output Z);assign Z=D;
`ifdef VCS_REFERENCE
reg notifier=0;always @(notifier) if($time>0) $display("CHECK kind=SETUP time=%0t",$time);
`endif
specify (D=>Z)=0; $hold(posedge C,D,0); endspecify endmodule
