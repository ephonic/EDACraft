`timescale 1ns/1ps
module top;
  logic [7:0] a=0,b=0;
  logic ea=1,eb=0;
  wire [7:0] bus;
  wire [7:0] delayed;
  bit [7:0] clean=0;
  integer changes=0,i;
  assign bus=ea?a:8'bz;
  assign bus=eb?b:8'bz;
  assign #2 delayed=bus;
  always @(bus)changes=changes+1;
  initial begin
    #1;
    for(i=0;i<8;i=i+1)begin
      a=i*31;b=~a;eb=i[0];
      if(i==3)a=8'bx10z0011;
      if(i==4)begin ea=0;eb=0;end
      else ea=1;
      clean=a;
      #3;$display("TRACE stores %0d %b %b %h %0d",i,bus,delayed,clean,changes);
    end
    force bus=8'ha5;
    #3;$display("TRACE forced %h %h",bus,delayed);
    a=8'h12;b=8'h12;ea=1;eb=1;
    release bus;
    #3;$display("TRACE release %h %h",bus,delayed);
    a<=#2 8'hff;b<=#2 8'hff;
    #5;$display("TRACE nba %h %h",bus,delayed);
    #1;$finish;
  end
endmodule
