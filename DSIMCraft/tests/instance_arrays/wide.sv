`timescale 1ns/1ps
module wide_lane #(parameter W=70)(input wire[W-1:0] a,output wire[W-1:0] y);
  assign y=a;
endmodule
module top;
  logic[209:0] data;
  logic[96:0] hi;logic[112:0] lo;
  wire[209:0] y;bit[209:0] clean;
  wide_lane u[1:-1](data,y),v[3:5](data,{hi,lo}),b[2:0](data,clean);
  initial begin
    data=210'h123456789abcdef0123456789abcdef0123456789abcdef012345;#1;
    $display("TRACE wide %h %h",y,{hi,lo});
    if(y!==data||{hi,lo}!==data||clean!==data)$fatal(1,"wide slices");
    data=0;data[209]=1'bx;data[140]=1'bz;data[139]=1;data[70]=1;data[69]=1;data[0]=1'bx;#1;
    $display("TRACE boundary %b %b %b %b %b %b",y[209],y[140],y[139],y[70],y[69],y[0]);
    if(y!==data||{hi,lo}!==data||clean[209]!==0||clean[140]!==0||clean[0]!==0||clean[139]!==1)$fatal(1,"wide xz");
    $finish;
  end
endmodule
