`timescale 1ns/1ps
module top;
logic [7:0] raw;
logic signed [7:0] neg;
logic [129:0] wide;
logic [63:0] a,b,c,d,e,f,g;
logic [7:0] h,i,j;
int checks;
initial begin
 raw=8'hff;neg=-1;wide=0;checks=0;
 a=longint'(32'hffffffff+1);
 b=longint'(32'hffffffff);
 c=64'(32'hffffffff+1);
 d=64'(neg);
 e=64'(raw);
 f=unsigned'(longint'(neg));
 g=integer'(8'hff);
 h=byte'(16'h80ff);i=shortint'(32'h12345678);j=bit'(8'hfe);
 assert(a==64'h100000000)checks++;
 assert(b==64'hffffffff)checks++;
 assert(c==a)checks++;
 assert(d==64'hffffffffffffffff)checks++;
 assert(e==255)checks++;
 assert(f==d)checks++;
 assert(g==255)checks++;
 assert(h==255&&i==8'h78&&j==0)checks++;
 #1;
 raw=8'b10xz01z1;neg=8'bx100zz01;
 a=int'(raw);b=integer'(raw);c=time'(neg);
 h=byte'(raw);i=8'(raw);j=logic'(raw);
 wide=130'(signed'(8'h80));
 #1;
 a=longint'(8'sh80);b=longint'(8'h80);c=64'(signed'(raw));
 d=64'(unsigned'(neg));e=longint'(32'hffffffff+32'd2);
 wide=130'(1)<<129;
 #1;
 $display("TRACE values %0d %h %h %h %h %h",checks,a,b,d,e,wide);
 $finish;
end
endmodule
