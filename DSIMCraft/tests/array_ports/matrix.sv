`timescale 1ns/1ps
module matrix(input logic[7:0]a[2:1][5:6],output logic[7:0]q[7:8][4:3]);
 assign q[7][4]=a[2][5]+1,q[7][3]=a[2][6]+2,q[8][4]=a[1][5]+3,q[8][3]=a[1][6]+4;
wire [31:0] observe_a={a[2][6],a[2][5],a[1][6],a[1][5]};
wire [31:0] observe_q={q[8][4],q[8][3],q[7][4],q[7][3]};
endmodule
module middle(input logic[7:0]a[0:1][9:8],output logic[7:0]q[3:2][0:1]);
 matrix m(a,q);
wire [31:0] observe_a={a[1][9],a[1][8],a[0][9],a[0][8]};
wire [31:0] observe_q={q[3][1],q[3][0],q[2][1],q[2][0]};
endmodule
module top;
 logic[7:0]bank[4:5][0:1][9:8],q[3:2][0:1];middle u(.a(bank[5]),.q(q));
wire [63:0] observe_bank={bank[5][1][9],bank[5][1][8],bank[5][0][9],bank[5][0][8],bank[4][1][9],bank[4][1][8],bank[4][0][9],bank[4][0][8]};
wire [31:0] observe_q={q[3][1],q[3][0],q[2][1],q[2][0]};
initial begin
 foreach(bank[i,j,k])bank[i][j][k]=8'hee;
 bank[5][0][9]=1;bank[5][0][8]=2;bank[5][1][9]=3;bank[5][1][8]=4;
 #1 $display("TRACE matrix %h",observe_q);
 if(observe_q!==32'h04020806||bank[4][0][9]!==8'hee)$fatal(1,"matrix first");
 bank[5][1][8]<=8'hff;
 #1 $display("TRACE matrix %h",observe_q);
 if(observe_q!==32'h04020306)$fatal(1,"matrix final");$finish;
 end
endmodule
