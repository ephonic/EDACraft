`timescale 1ns/1ps
module lane #(parameter W=4)(input wire [W-1:0] a,input wire en,output wire [W-1:0] y);
  assign y=en?a: {W{1'bz}};
endmodule
module top;
  logic[11:0] data;logic enable;
  wire[11:0] up,down;wire[3:0] shared;
  lane u[-1:1](data,enable,up),d[4:2](data,enable,down),b[2:0](4'ha,enable,shared);
  initial begin
    data=12'h123;enable=1;#1;
    $display("TRACE map %h %h %h",up,down,shared);
    if(up!==12'h123||down!==up||shared!==4'ha)$fatal(1,"split/broadcast");
    data=12'hxz5;#1;$display("TRACE four %h %h",up,down);
    if(up!==data||down!==data)$fatal(1,"four state");
    enable=0;#1;$display("TRACE off %h %h %h",up,down,shared);
    if(up!==12'hzzz||down!==up||shared!==4'hz)$fatal(1,"broadcast disable");
    $finish;
  end
endmodule
