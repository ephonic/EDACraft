`timescale 1ns/1ps
module bus_cell(input wire drive,input wire[3:0] value,inout wire[3:0] bus,output wire[3:0] sense);
  assign bus=drive?value:4'bz;
  assign sense=bus;
endmodule
module reverse_cell(input wire p,input wire drive);assign p=drive?1'b1:1'bz;endmodule
module top;
  logic[1:0] drive;logic[7:0] value,external_value;logic external_enable;
  tri[7:0] bus;wire[7:0] sense;wire[1:0] back;
  assign bus=external_enable?external_value:8'hzz;
  bus_cell c[0:1](drive,value,bus,sense);
  reverse_cell r[1:0](back,drive);
  initial begin
    drive=2'b10;value=8'ha5;external_enable=0;external_value=0;#1;
    $display("TRACE net %h %h %b",bus,sense,back);
    if(bus!==8'haz||sense!==bus||back!==2'b1z)$fatal(1,"net links");
    external_enable=1;external_value=8'h3c;#1;
    $display("TRACE resolve %h %h",bus,sense);if(bus!==8'bx01x1100)$fatal(1,"resolution");
    drive=0;#1;$display("TRACE outside %h %h",bus,sense);
    if(bus!==8'h3c||sense!==bus)$fatal(1,"external drive");
    external_enable=0;#1;if(bus!==8'hzz||sense!==bus)$fatal(1,"release");
    $finish;
  end
endmodule
