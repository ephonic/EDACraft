`timescale 1ns/1ps
module ram(input clk,input we,input [3:0] addr,input [7:0] din,output [7:0] dout);
  reg [7:0] mem [2:13];
  wire [95:0] state={mem[13],mem[12],mem[11],mem[10],mem[9],mem[8],mem[7],mem[6],mem[5],mem[4],mem[3],mem[2]};
  always @(posedge clk) if(we) mem[addr] <= #2 din;
  assign dout=mem[addr];
endmodule
module top;
  reg clk,we;
  reg [3:0] addr;
  reg [7:0] din;
  wire [7:0] dout;
  ram u(clk,we,addr,din,dout);
  reg [7:0] asc [2:5];
  reg [7:0] desc [5:2];
  reg [79:0] wide [0:2];
  reg [3:0] i,b;
  reg [79:0] huge;
  wire [7:0] r=asc[i];
  wire [3:0] nib=asc[i][b+:4];
  reg [7:0] comb;
  always_comb comb=desc[i];
  wire [31:0] asc_state={asc[5],asc[4],asc[3],asc[2]};
  wire [31:0] desc_state={desc[5],desc[4],desc[3],desc[2]};
  wire [239:0] wide_state={wide[2],wide[1],wide[0]};
  initial begin
    clk=0;we=0;addr=2;din=0;i=2;b=0;huge=0;
    asc[2]=8'h12;asc[3]=8'h34;asc[4]=8'h56;asc[5]=8'h78;
    desc[2]=8'h90;desc[3]=8'hab;desc[4]=8'hcd;desc[5]=8'hef;
    wide[0]=80'h0123456789abcdef0123;wide[1]='x;wide[2]='z;
    #1 $display("TRACE init %h %h %h %h %h",r,nib,comb,wide[0],dout);
    i=3;b=4;asc[i][b+:4]=4'hf;
    #1 $display("TRACE part %h %h %h",r,nib,comb);
    {asc[i],desc[i][3:0]}=12'ha5c;
    i=4;asc[i]<=#2 8'hde;i=5;
    asc[i][b-:4]<=#2 4'h9;b=0;
    wide[2][i+:8]=8'h5a;
    #3 $display("TRACE nba %h %h %h %h %h",asc[3],desc[3],asc[4],asc[5],wide[2]);
    addr=11;din=8'hc7;we=1;clk=1;
    #1 addr=12;din=8'hff;
    #2 addr=11;
    #1 $display("TRACE ram %h",dout);
    i=2;asc[i]=#2 8'h81;
    #1 $display("TRACE block %h %h",asc[2],asc[3]);
    i=1;asc[i]=0;
    #1 $display("TRACE outside %h %h",r,nib);
    i='x;asc[i]=0;wide[i][b+:4]=0;
    #1 $display("TRACE unknown %h %h %h",r,comb,wide[i]);
    huge=80'h10000000000000000000;
    asc[huge]=0;
    #1 $display("TRACE huge %h %h %h",asc[huge],asc[2],asc[5]);
    $finish;
  end
  initial begin
    #11 i=3;
  end
endmodule
