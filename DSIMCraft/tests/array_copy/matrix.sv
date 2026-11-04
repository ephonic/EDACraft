`timescale 1ns/1ps
module top;
 logic[7:0]a[3:2][7:6][1:2],b[4:5][0:1][9:8],row[0:1][5:4];
wire [63:0] observe_a={a[3][7][2],a[3][7][1],a[3][6][2],a[3][6][1],a[2][7][2],a[2][7][1],a[2][6][2],a[2][6][1]};
wire [63:0] observe_b={b[5][1][9],b[5][1][8],b[5][0][9],b[5][0][8],b[4][1][9],b[4][1][8],b[4][0][9],b[4][0][8]};
wire [31:0] observe_row={row[1][5],row[1][4],row[0][5],row[0][4]};
 initial begin
 foreach(a[i,j,k])a[i][j][k]=(i-2)*40+(j-6)*10+k;
 b=a;row=a[3];a[2]=a[3];b=b;
 #1 $display("TRACE matrix %h %h %h %h %h",b[4][0][9],b[5][1][8],row[0][5],row[1][4],a[2][7][1]);
 if(b[4][0][9]!==51||b[5][1][8]!==2||row[0][5]!==51||row[1][4]!==42||a[2][7][1]!==51)$fatal(1,"matrix copy");
 b[5]<=#2 a[3];a[3][7][1]=8'hff;
 #3 $display("TRACE sampled %h %h",b[5][0][9],b[5][1][8]);
 if(b[5][0][9]!==51||b[5][1][8]!==42)$fatal(1,"subarray NBA");$finish;
 end
endmodule
