`timescale 1ns/1ps
module top;
bit flag;bit signed[7:0] sb;bit[129:0] wide;
byte b;byte unsigned ub;shortint s;shortint unsigned us;
int i;int unsigned ui;longint l;longint unsigned ul;integer four;
reg[79:0] extended;
initial begin
$display("TRACE defaults %h %h %h %h %h %h %h %h",flag,b,s,i,l,wide,sb,four);
b=8'b1xz001zx;ub=8'hf0;s=16'hf100;us=16'hf100;i=32'hf0000000;ui=32'hf0000000;l=64'hf000000000000000;ul=64'hf000000000000000;
sb=8'h80;wide=130'h3ffffffffffffffffffffffffffffffff;wide[110:63]=48'b1x0z;
$display("TRACE values %h %0d %0d %0d %0d %0d %0d %0d %0d %h",b,b,ub,s,us,i,ui,l,ul,wide);
extended=b;$display("TRACE extend %h",extended);extended=ub;$display("TRACE extend %h",extended);extended=l;$display("TRACE extend %h",extended);
b>>>=2;ub>>>=2;s>>>=3;us>>>=3;l>>>=4;ul>>>=4;
$display("TRACE shifts %h %h %h %h %h %h",b,ub,s,us,l,ul);
i=32'hx;ui=32'hz;l=64'b10xz01zx;flag=1'bx;sb=8'b1xz001zx;
$display("TRACE convert %h %h %h %h %h",i,ui,l,flag,sb);
b+=8'bx;wide^=130'bz;$display("TRACE compound %h %h",b,wide);
#1;$finish;
end
endmodule
