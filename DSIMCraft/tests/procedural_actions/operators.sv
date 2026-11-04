`timescale 1ns/1ps
module top;
reg signed [15:0] a=-16'sd123;
reg [7:0] u=250;
reg signed [129:0] wide=-130'sd65537;
reg [79:0] bits=80'h123456789abcdef01234;
reg [7:0] unknown=8'hx5;
initial begin
 #1;u+=10;a+=3;a/=7;a%=5;a*=9;a-=2;
 $display("TRACE arithmetic %0d %0d",a,u);
 #1;a<<=2;a>>>=3;a>>=2;a<<<=1;
 wide>>>=16;wide*=130'sd3;wide-=130'sd1;
 bits&=80'hffff0000ffff0000ffff;bits^=80'h123456789abcdef01234;bits|=80'h00000000000000000003;
 $display("TRACE shifts %h %h %h",a,wide,bits);
 #1;unknown^=8'hf0;u/=0;
 $display("TRACE unknown %h %h",unknown,u);
 #1;$finish;
end
endmodule
