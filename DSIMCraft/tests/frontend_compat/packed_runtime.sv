`timescale 1ns/1ps
module top;
  logic [2:1][7:4] d;
  logic [0:1][4:7] a;
  logic [1:0][-1:-4] n;
  logic [1:0][79:0] wide;
  logic [1:0][7:0] mem[0:1];
  bit [1:0][3:0] two;
  integer r, c, m, effects=0;
  logic [127:0] high;
  wire [3:0] row=d[r];
  function automatic integer pick(input integer x);
    effects++;return x;
  endfunction
  initial begin
    d=8'ha5;a=8'ha5;n=8'ha5;two=8'hxz;
    wide=160'h123456789abcdef00123_fedcba9876543210abcd;
    mem[0]=16'h1234;mem[1]=16'h5678;
    r=2;c=7;m=1;#1;
    if(d[r]!==4'ha||row!==4'ha||d[r][c]!==1||a[0][4]!==1||n[1][-1]!==1) $fatal(1,"shape/index");
    if($bits(d)!==8||$bits(d[r])!==4||$size(d,1)!==2||$size(d,2)!==4||$left(d,1)!==2||$right(d,2)!==4||$dimensions(d)!==2) $fatal(1,"queries");
    $display("TRACE shape %h %h %b %0d %0d %0d",d[r],a[0],n[1][-1],$bits(d[r]),$size(d,2),$dimensions(d));
    r=0;c=3;
    if(wide[r]!==80'hfedcba9876543210abcd||mem[m][r]!==8'h78||mem[m][r][c]!==1) $fatal(1,"memory/wide");
    mem[m][r][c]=0;
    wide[r][c]=0;
    $display("TRACE storage %h %h",mem[1],wide[0]);
    r=2;c=6;
    d[pick(r)][pick(c)]++;
    if(effects!==2||d!==8'he5) $fatal(1,"compound evaluated index twice");
    d[pick(r)]<=#2 4'h3;r=1;#3;
    if(d!==8'h35||effects!==3) $fatal(1,"NBA address sampling");
    $display("TRACE update %h %0d",d,effects);
    r=3;c=5;
    if(d[r][c]!==1'bx) $fatal(1,"row index wrapped");
    d[r][pick(c)]=0;
    if(d!==8'h35||effects!==4) $fatal(1,"invalid store");
    r=1;c=8;
    if(d[r][c]!==1'bx||two[0][c]!==1'b0) $fatal(1,"bit index wrapped");
    c=-2;
    if(n[1][c]!==1'b0) $fatal(1,"negative bound");
    high=128'h10000000000000000;
    if(d[high]!==4'hx) $fatal(1,"wide high index truncated");
    high='x;
    if(d[1][high]!==1'bx) $fatal(1,"unknown index");
    $display("TRACE invalid %h %b %0d",d[3],two[0][8],effects);
    $finish;
  end
endmodule
