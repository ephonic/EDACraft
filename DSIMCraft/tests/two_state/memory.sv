`timescale 1ns/1ps
module top;
int words[0:2];byte bytes[1:2];bit[79:0] wide[0:1];integer index;int value;bit[7:0] bits;
initial begin
$display("TRACE defaults %h %h %h",words[0],bytes[1],wide[0]);
words[0]=32'hx1z2;words[1]=-1;words[2]=3;bytes[1]=8'b1xz001zx;wide[0]=80'hxz123456789abcdef012;
index=10;value=words[index];bits=wide[0][index+:8];
$display("TRACE read %h %h %h %h %h",words[0],bytes[1],wide[0],value,bits);
index=32'hx;value=words[index];bits=bits[index];$display("TRACE unknown %h %h",value,bits);
index=10;value=++words[index];$display("TRACE prefix %h %h",value,words[0]);
index=0;words[index]<=#1 32'hxz123456;wide[1]<=#1 80'hxz123456789abcdef012;bytes[2]<=#1 8'hxz;
#2;$display("TRACE nba %h %h %h",words[0],wide[1],bytes[2]);
$readmemh("data.hex",words);$display("TRACE file %h %h %h",words[0],words[1],words[2]);#1;$finish;
end
endmodule
