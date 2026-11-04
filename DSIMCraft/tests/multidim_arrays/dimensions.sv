`timescale 1ns/1ps
module top;
logic [15:8] a[2:1][4:5][7:6];
wire [63:0] image={a[1][4][6],a[1][4][7],a[1][5][6],a[1][5][7],a[2][4][6],a[2][4][7],a[2][5][6],a[2][5][7]};
integer visits=0,order=0,x,y,z;logic[127:0] wide;logic[7:0] q;
initial begin
 foreach(a[i,j,k]) begin a[i][j][k]=i*32+j*4+k;visits++;order=order*3+i+j+k;end
 if(visits!==8 || a[1][4][6]!==54 || a[2][5][7]!==91)$fatal(1,"3D fill");
 x=1;y=4;z=6;wide=128'h10000000000000001;
 q=a[x][y][z];if(q!==54)$fatal(1,"dynamic read");
 q=a[wide][y][z];if(q!==8'hxx)$fatal(1,"wide index");
 x=-1;q=a[x][y][z];if(q!==8'hxx)$fatal(1,"negative index");
 x=32'bx;q=a[x][y][z];if(q!==8'hxx)$fatal(1,"unknown dimension");
 x=1;y=32'bz;q=a[x][y][z];if(q!==8'hxx)$fatal(1,"Z dimension");
 x=1;y=6;q=a[x][y][z];if(q!==8'hxx)$fatal(1,"row alias");
 a[x][y][z]=0;x=3;y=4;a[x][y][z]=0;
 x=1;y=4;z=6;a[x][y][z][11:8]=4'hf;
 if(a[1][4][6]!==8'h3f)$fatal(1,"packed select");
 #1;a[x][y][z][12+:3]=3'b101;
 if(a[1][4][6]!==8'h5f)$fatal(1,"dynamic part select");
 #1;$display("TRACE dimensions %0d %h",visits,image);
 #1;
end
endmodule
