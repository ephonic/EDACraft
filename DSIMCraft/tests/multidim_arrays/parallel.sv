`timescale 1ns/1ps
module top;
logic[3:0] a[1:2][3:4],b[1:2][3:4];integer sa=0,sb=0,ea=0,eb=0;
wire[15:0] image_a={a[1][3],a[1][4],a[2][3],a[2][4]};
wire[15:0] image_b={b[1][3],b[1][4],b[2][3],b[2][4]};
initial begin foreach(a[i,j])a[i][j]=0;foreach(a[i,j])begin #2;a[i][j]=i+j;sa+=a[i][j];end if(sa!==20)ea=1;end
initial begin foreach(b[i,j])b[i][j]=0;foreach(b[i,j])begin #3;b[i][j]=i+j;sb+=b[i][j];end if(sb!==20)eb=1;end
endmodule
