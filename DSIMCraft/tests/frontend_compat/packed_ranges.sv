`timescale 1ns/1ps
module top;
  logic [3:1][7:4] d;
  logic [1:3][4:7] a;
  logic [1:0][-1:-4] n;
  integer r, c;
  initial begin
    d=12'habc;a=12'habc;n=8'ha5;r=2;c=5;#1;
    if(d[3:2]!==8'hab||a[1:2]!==8'hab||d[r][c+:2]!==2'b01||a[r][c+:2]!==2'b01) $fatal(1,"valid range");
    $display("TRACE ranges %h %h %b %b",d[3:2],a[1:2],d[r][c+:2],a[r][c+:2]);
    c=3;
    if(d[r][c+:3]!==3'bxxx||a[r][c+:3]!==3'bxxx) $fatal(1,"partial lower range");
    $display("TRACE partial %b %b",d[r][c+:3],a[r][c+:3]);
    d[r][c+:3]=3'b000;a[r][c+:3]=3'b111;
    if(d!==12'habc||a!==12'habc) $fatal(1,"clipped range store");
    r=0;
    if(d[r+:2]!==8'hxx||a[r+:2]!==8'hxx) $fatal(1,"partial outer range");
    c=-5;
    if(n[1][c+:3]!==3'bxxx) $fatal(1,"negative partial range");
    $display("TRACE clipped %h %h %h %h %b",d,a,d[r+:2],a[r+:2],n[1][c+:3]);
    $finish;
  end
endmodule
