`timescale 1ns/1ps
module top;
typedef logic[129:0] wide_t;
typedef enum logic[1:0]{ZERO,ONE} kind_t;
integer a=0,b=0,c=0;
task automatic work(input integer n,output integer value);
 static integer calls=0;
 static integer words[1:2];
 static wide_t wide=130'h200000000000000000000000000000003;
 static bit[7:0] clean;
 static kind_t kind=ONE;
 static logic unknown;
 integer local_value=n;
 if(calls==0)begin
  if(words[1]!==32'hxxxxxxxx||clean!==0||unknown!==1'bx||kind!=ONE||wide[129]!==1)$fatal(1,"static defaults");
  words[1]=0;words[2]=0;
 end
 calls++;
 words[1]+=n;words[2]<=#1 words[1]+10;
 wide[7:0]+=n;
 #2;
 value=words[1]*100+words[2]*10+local_value;
endtask
initial begin
 work(1,a);work(2,b);work(3,c);
 $display("TRACE storage %0d %0d %0d",a,b,c);
 if(a!=211||b!=432||c!=763)$fatal(1,"static array/NBA persistence");
end
endmodule
