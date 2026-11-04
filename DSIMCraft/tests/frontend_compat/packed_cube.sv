`timescale 1ns/1ps
module legacy_ports(a,y);
  input [1:0][1:0][3:0] a;
  output [1:0][1:0][3:0] y;
  assign y=a;
endmodule
module top;
  logic [1:0][1:0][3:0] cube;
  wire [1:0][1:0][3:0] y;
  integer i,j,k;
  legacy_ports dut(cube,y);
  initial begin
    cube=16'h1234;i=1;j=0;k=1;#1;
    if(y[i][j]!==4'h2||y[i][j][k]!==1||$size(cube,3)!==4||$bits(cube[i])!==8) $fatal(1,"3D shape");
    cube[i][j][k]=0;#1;
    if(y!==16'h1034) $fatal(1,"3D store");
    $display("TRACE cube %h %h %0d %0d",y,y[i],$dimensions(cube),$bits(cube[i]));
    $finish;
  end
endmodule
