module bank(input clk,en,input [4:0] addr,input din,output reg dout);
 reg mem[31:0];
 always @(posedge clk)begin
  if(en)begin mem[addr]<=din;dout<=din;end
  else dout<=mem[addr];
 end
endmodule
module top;
 reg clk=0,en=0;reg [4:0] addr=17;reg [11:0] data=12'ha35;wire [11:0] q;
 for(genvar k=0;k<12;k++)begin: banks
  bank ram(clk,en,addr,data[k],q[k]);
 end
 initial begin
  #1;en=1;#1;clk=1;#1;clk=0;en=0;#1;clk=1;#1;
  $display("TRACE registration %h %b",q,q[9]);
  clk=0;addr=18;#1;clk=1;#1;$display("TRACE uninitialized %h",q);
  clk=0;addr=18;data=12'h59a;en=1;#1;clk=1;#1;clk=0;en=0;addr=17;#1;clk=1;#1;
  $display("TRACE independent %h",q);$finish;
 end
endmodule
