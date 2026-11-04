`timescale 1ns/1ps
module top;
time words[0:2];integer unsigned numbers[0:1];
time old=0;reg signed[63:0] negative=-1;
integer index=0;
initial begin
 words[0]=64'h12345678ffffffff;words[1]=64'h8000000000000000;words[2]=64'hffffffffffffffff;
 numbers[0]=32'hffffffff;numbers[1]=32'h80000000;
 #1;old=words[index++]++;numbers[0]/=3;
 words[index++][32+:32]+=1;
 words[index++]<=#2 64'hfedcba9876543210;
 $display("TRACE memory %h %h %h %0d %0d",old,words[0],words[1],numbers[0],index);
 #1;negative=words[0][0+:32];numbers[1]>>>=1;
 $display("TRACE selects %h %0d",negative,numbers[1]);
 #2;$display("TRACE delayed %h",words[2]);$finish;
end
endmodule
