`timescale 1ns/1ps
module extend(input signed [7:0] a,output signed [7:0] y);
 assign y=a;
endmodule
module top;
 reg signed [7:0] a,b;
 reg [7:0] u;
 reg [3:0] amount;
 reg c;
 reg signed [15:0] stored,blocking_value;
 reg signed [7:0] mem[0:3];
 reg signed [7:0] address;
 wire signed [15:0] sum=a+b,diff=a-b,mul=a*b,quot=a/b,rem=a%b;
 wire signed [15:0] sx=a,arith=a>>>amount,logical=a>>amount;
 wire [15:0] mixed=a+u,partial=a[7:0],cast_signed=$signed(u),cast_unsigned=$unsigned(a);
 wire signed [15:0] choice=c?a:b;
 wire [15:0] mixed_choice=c?a:u;
 wire [15:0] concat_one={a},concat_two={a,b};
 wire signed [15:0] port;
 wire signed [15:0] memory_value=mem[address];
 wire [7:0] rel={a<b,a<=b,a>b,a>=b,a==b,a!=b,a===b,a!==b};
 wire [15:0] mixed_rel={15'b0,a<u};
 extend child(a,port);
 initial begin
  a=-7;b=3;u=8'h80;amount=2;c=1;stored=0;blocking_value=0;
  mem[0]=-3;mem[1]=8'sh81;mem[2]='x;mem[3]='z;address=0;
  #1 $display("TRACE math %0d %0d %0d %0d %0d",sum,diff,mul,quot,rem);
  $display("TRACE types %h %h %h %h %h %h %h %h",sx,mixed,partial,cast_signed,cast_unsigned,choice,mixed_choice,port);
  $display("TRACE shift %h %h %h %h",arith,logical,a<<<amount,$unsigned(a)>>>amount);
  $display("TRACE decimal %d %0d %d %0d %h",a,a,quot,quot,concat_two);
  $display("TRACE compare %b mixed=%b concat=%h mem=%h",rel,mixed_rel,concat_one,memory_value);
  stored<=#2 a+b;a=-8;b=-3;c=0;address=1;
  #3 $display("TRACE nba %0d current=%0d %0d mem=%h",stored,quot,rem,memory_value);
  blocking_value=#2 a-b;
  #1 $display("TRACE block %0d",blocking_value);
  a=8'sbxxxx0011;b=8'sbzzzz0011;address=2;
  #1 $display("TRACE unknown %b %b %b %b %b",sx,arith,logical,choice,memory_value);
  address=-1;
  #1 $display("TRACE address %h",memory_value);
  address=0;mem[address]<=#1 -5;
  #2 $display("TRACE mem %0d",memory_value);
  $finish;
 end
 initial begin #5 a=12;b=2;end
endmodule
