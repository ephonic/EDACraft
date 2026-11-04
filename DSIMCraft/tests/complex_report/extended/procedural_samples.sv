`timescale 1ns/1ps
module tb;
  reg clk=0;
  reg [7:0] v=0,previous=0;
  reg [7:0] p=0,gated=0;
  reg enabled=0;
  integer tick=0;
  always #5 clk=~clk;
  // X -> 0 at time zero is also a negedge; exclude startup stimulus.
  always @(negedge clk)if(tick>0)begin v=v+1;enabled=~enabled;end
  always @(posedge clk)begin
    tick=tick+1;
    if(tick%2==0)p=$past(v);
    gated=$past(v,1,enabled);
  end
  initial begin
    #36;
    if(p!==2||gated!==1)$fatal(1,"conditional/gated history %d %d",p,gated);
    $display("TRACE procedural %0d %0d",p,gated);$finish;
  end
endmodule
