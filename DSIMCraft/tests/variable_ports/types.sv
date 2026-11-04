`timescale 1ns/1ps
module wide(input signed [129:0] d,output signed [129:0] y);
 assign y=d;
endmodule
module nibble(input [3:0] d,output [3:0] y);
 assign y=d;
endmodule
module bits(input [1:0] d,output [1:0] y);assign y=d;endmodule
module top;
 typedef struct packed {logic [3:0] hi;bit [3:0] lo;} Pair;
 Pair pair;
 logic signed [129:0] d;
 logic signed [135:0] y;
 bit [129:0] two;
 logic [3:0] words[0:1][2:3];
 wire [15:0] image;
 logic [3:0] n;
 wire [3:0] mirror;
 logic [1:0] member_bits;
 wide w0(d,y);
 wide w1(d,two);
 nibble a(n,pair.hi);
 nibble b(n,pair.lo);
 nibble c(n,words[0][2]);
 nibble e(n,words[0][3]);
 nibble f(n,words[1][2]);
 nibble g(n,words[1][3]);
 nibble h(words[1][3],mirror);
 bits m(pair.hi[1:0],member_bits);
 assign image={words[0][2],words[0][3],words[1][2],words[1][3]};
 initial begin
  d=-130'sd3;n=4'h9;
  #1;
  if(mirror!==n||member_bits!==n[1:0])$fatal(1,"selected port receiver");
  $display("TRACE types %h %h %h %h",y,two,pair,image);
  if(y!==-136'sd3||two!==-130'sd3||pair!==8'h99||image!==16'h9999)$fatal(1,"types first");
  d=130'h200000000000000000000000000000005;n=4'bxz01;
  #1;
  if(mirror!==n||member_bits!==n[1:0])$fatal(1,"selected port receiver");
  $display("TRACE types %h %h %b %b",y,two,pair,image);
  if(y!==136'hfe00000000000000000000000000000005||pair!==8'bxz01xz01||pair.lo!==4'b0001||image!==16'bxz01xz01xz01xz01)$fatal(1,"types sign and field");
  d=130'h123456789abcdef0123456789abcdef01;n=4'h6;
  #1;
  if(mirror!==n||member_bits!==n[1:0])$fatal(1,"selected port receiver");
  $display("TRACE types %h %h %h %h",y,two,pair,image);
  if(y!==136'h123456789abcdef0123456789abcdef01||pair!==8'h66||image!==16'h6666)$fatal(1,"types final");
  $finish;
 end
endmodule
