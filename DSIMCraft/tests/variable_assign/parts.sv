`timescale 1ns/1ps
module top;
 typedef struct packed {logic[3:0] hi;logic[3:0] lo;} Pair;
 Pair p;
 logic [7:0] d;
 logic [15:4] q;
 logic [7:0] mixed;
 wire [7:0] netpart;
 logic [3:0] repeated;
 integer i;
 assign {q[15:12],q[7:4]}=d;
 assign {netpart[7:4],mixed[3:0]}=d;
 assign #0.1 {repeated,repeated}=d;
 assign p.hi=d[3:0];
 initial begin
  q[11:8]=4'h5;mixed[7:4]=4'ha;p.lo=0;d=8'h96;
  for(i=0;i<4;i=i+1)p.lo[i]=1;
  #1 $display("TRACE parts %h %h %b %h %h",q,mixed,netpart,repeated,p);
  if(q!==12'h956||mixed!==8'ha6||netpart!==8'b1001zzzz||repeated!==6||p!==8'h6f)$fatal(1,"parts first");
  q[11:8]<=3;d<=8'h2b;p.lo[2]=0;
  #1 $display("TRACE parts %h %h %b %h %h",q,mixed,netpart,repeated,p);
  if(q!==12'h23b||mixed!==8'hab||netpart!==8'b0010zzzz||repeated!==11||p!==8'hbb)$fatal(1,"parts final");
  $finish;
 end
endmodule
