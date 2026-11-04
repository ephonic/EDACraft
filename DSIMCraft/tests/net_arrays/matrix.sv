`timescale 1ns/1ps
module leaf(input wire[7:0]a[3:2][4:5],input logic en);
 assign a[3][4]=en?8'h11:8'hzz,a[3][5]=en?8'h22:8'hzz;
 assign a[2][4]=en?8'h33:8'hzz,a[2][5]=en?8'h44:8'hzz;
wire [31:0] observe_a={a[3][5],a[3][4],a[2][5],a[2][4]};
endmodule
module middle(inout tri[7:0]a[7:6][0:1],input logic en);
 leaf u(a,en);
wire [31:0] observe_a={a[7][1],a[7][0],a[6][1],a[6][0]};
endmodule
module top;
 tri[7:0]bank[4:5][2:3][9:8];logic en,host;
 middle m(bank[5],en);
 assign bank[5][2][9]=host?8'hff:8'hzz;
wire [63:0] observe_bank={bank[5][3][9],bank[5][3][8],bank[5][2][9],bank[5][2][8],bank[4][3][9],bank[4][3][8],bank[4][2][9],bank[4][2][8]};
 initial begin en=1;host=0;
 #1 $display("TRACE matrix %h %h %h %h %h",bank[5][2][9],bank[5][2][8],bank[5][3][9],bank[5][3][8],bank[4][2][8]);
 if(bank[5][2][9]!==8'h11||bank[5][2][8]!==8'h22||bank[5][3][9]!==8'h33||bank[5][3][8]!==8'h44||bank[4][2][8]!==8'hzz)$fatal(1,"matrix");
 host=1;#1 $display("TRACE clash %h %h",bank[5][2][9],bank[5][2][8]);
 if(bank[5][2][9]!==8'bxxx1xxx1||bank[5][2][8]!==8'h22)$fatal(1,"matrix clash");
 en=0;host=0;#1 $display("TRACE release %h %h",bank[5][2][9],bank[5][3][8]);
 if(bank[5][2][9]!==8'hzz||bank[5][3][8]!==8'hzz)$fatal(1,"matrix release");$finish;
 end
endmodule
