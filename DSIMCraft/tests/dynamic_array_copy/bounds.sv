`timescale 1ns/1ps
module top;
logic[129:0]a[3:2][7:6],row[0:1];bit[129:0]two[0:1],src2[3:2][7:6];
logic[7:0]cube[0:1][0:1][1:2],row8[0:1];integer i,j,calls;logic[129:0]idx;
function automatic integer touch(input integer v);begin calls=calls+1;touch=v;end endfunction
initial begin
calls=0;a[3][7]=130'h200000000000000000000000000000001;a[3][6]=130'h100000000000000000000000000000002;a[2][7]='z;a[2][6]='x;
src2[3][7]=7;src2[3][6]=8;idx=3;row=a[idx];#1;
if(row[0]!==130'h200000000000000000000000000000001||row[1]!==130'h100000000000000000000000000000002)$fatal(1,"wide values");
idx=130'h100000000000000000000000000000003;row=a[idx];two=a[idx];#1;if(row[0]!==130'bx||row[1]!==130'bx||two[0]!==0||two[1]!==0)$fatal(1,"wide invalid");
idx=130'bx;row=a[idx];#1;if(row[0]!==130'bx||row[1]!==130'bx)$fatal(1,"unknown");
row=src2[idx];#1;if(row[0]!==0||row[1]!==0)$fatal(1,"two state default");
i=-1;row=a[i];a[i]=row;#1;if(row[0]!==130'bx||a[3][7]!==130'h200000000000000000000000000000001)$fatal(1,"negative index");
row=a[9];a[1'bx]=row;#1;if(row[0]!==130'bx||a[3][6]!==130'h100000000000000000000000000000002)$fatal(1,"constant invalid");
i=8;j=0;row8=cube[touch(i)][touch(j)];#1;if(calls!==2||row8[0]!==8'bx||row8[1]!==8'bx)$fatal(1,"remaining effects");
$display("TRACE bounds %h %h %h %0d",row[0],two[0],row8[0],calls);$finish;
end
wire [519:0] observe_a={a[2][6],a[2][7],a[3][6],a[3][7]};
wire [259:0] observe_row={row[1],row[0]};
wire [259:0] observe_two={two[1],two[0]};
wire [519:0] observe_src2={src2[2][6],src2[2][7],src2[3][6],src2[3][7]};
wire [63:0] observe_cube={cube[1][1][2],cube[1][1][1],cube[1][0][2],cube[1][0][1],cube[0][1][2],cube[0][1][1],cube[0][0][2],cube[0][0][1]};
wire [15:0] observe_row8={row8[1],row8[0]};
endmodule
