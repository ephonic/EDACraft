`timescale 1ns/1ps
`ifndef DSIM_LANE_EPOCHS
`define DSIM_LANE_EPOCHS 3
`endif
`ifndef DSIM_LANE_INNER
`define DSIM_LANE_INNER 17
`endif
module lane #(parameter SEED=1);
`ifdef DSIM_LANE_UNKNOWN
 reg [31:0] acc=32'hxxxxxxxx;
`else
 reg [31:0] acc=SEED;
`endif
 integer epoch=0,i=0;
 initial begin
  for(epoch=0;epoch<`DSIM_LANE_EPOCHS;epoch=epoch+1) begin
   for(i=0;i<`DSIM_LANE_INNER;i=i+1) begin
    acc=acc*32'd1664525+32'd1013904223;
    acc=acc^(acc>>13);
   end
   #10;
  end
 end
endmodule
module top;
 lane #(.SEED(1)) a();
 lane #(.SEED(17)) b();
 lane #(.SEED(101)) c();
 lane #(.SEED(999)) d();
endmodule
