`timescale 1ns/1ps
module top;
logic [4:19] q;logic [-8:7] neg;integer i;logic signed[63:0] extreme;
logic[0:7] byte_q;logic [0:130] wide;
initial begin
 q=16'h96a5;neg=16'h96a5;byte_q=8'h96;wide=131'h5abcdef0123456789abcdef0123456789;
 #1;
 $display("TRACE CONST %h %h %b %b %b %h",q[4:7],q[16:19],q[4],q[19],neg[-8:-5],wide[0:66]);
 for(i=-2;i<=23;i=i+1)begin #1;$display("TRACE READ %0d %b %b %b",i,q[i],q[i+:5],q[i-:5]);end
 for(i=-11;i<=10;i=i+1)begin #1;$display("TRACE NEG %0d %b %b %b",i,neg[i],neg[i+:5],neg[i-:5]);end
 for(i=1;i<=22;i=i+1)begin
  q=16'h96a5;q[i+:5]=5'b10xz1;#1;$display("TRACE ADD %0d %b",i,q);
  q=16'h96a5;q[i-:5]=5'b10xz1;#1;$display("TRACE SUB %0d %b",i,q);
 end
 q=16'h96a5;i=7;q[i+++:3]=3'b110;#1;$display("TRACE SIDE %0d %h",i,q);
 byte_q=8'h96;i=2;byte_q[i+:3]<=#2 3'b001;i=5;#3;$display("TRACE NBA %h %0d",byte_q,i);
 extreme=64'sh8000000000000000;$display("TRACE EXTREME %b %b",q[extreme+:5],q[extreme-:5]);
 extreme=64'sh7fffffffffffffff;$display("TRACE EXTREME %b %b",q[extreme+:5],q[extreme-:5]);
 i='x;q[i+:5]=0;$display("TRACE UNKNOWN %b %b",q[i+:5],q);
 $finish;
end
endmodule
