`timescale 1ns/1ps
module top;
reg[79:0]words[0:2];
reg[79:0]prior=0;
reg[15:0]bits=16'h1234;
reg[7:0]out=0;
integer index=0,position=4,probe=0;
initial begin
 words[0]=80'hff;words[1]=80'h1234;words[2]=80'hffff;
 #1;prior=words[index++]++;
 $display("TRACE wordpost %h %h %0d",prior,words[0],index);
 prior=++words[index++];
 $display("TRACE wordpre %h %h %0d",prior,words[1],index);
 prior=words[index++][position++ +: 8]++;
 out=bits[position++ +: 4]++;
 $display("TRACE packedpost %h %h %h %h %0d %0d",prior,words[2],out,bits,index,position);
 out=--bits[position++ +: 4];
 $display("TRACE packedpre %h %h %0d",out,bits,position);
 #1;index=-1;prior=words[index++]++;
 words[-1]=++probe;
 $display("TRACE invalid %h %0d %0d",prior,index,probe);
 #1;position=17;out=bits[position-- -: 4]++;
 $display("TRACE partial %b %b %0d",out,bits,position);
 #1;$finish;
end
endmodule
