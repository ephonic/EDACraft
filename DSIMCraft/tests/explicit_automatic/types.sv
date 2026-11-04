`timescale 1ns/1ps
module top;
typedef logic [129:0] wide_t;
typedef enum logic [1:0] {ZERO,ONE} kind_t;
integer q=0,r=0;
function integer scan(input integer n);
 automatic integer total=n;
 automatic wide_t wide=130'h200000000000000000000000000000003;
 automatic bit [7:0] clean=8'hxz;
 automatic logic unknown;
 automatic kind_t kind=ONE;
 automatic integer words[1:2];
 integer calls=0;
 if(unknown!==1'bx||clean!==0||wide[129]!==1||kind!=ONE)return -1;
 if(words[1]!==32'hxxxxxxxx)return -2;
 words[1]=total;words[2]=words[1]+2;
 calls++;
 return words[1]*10+calls;
endfunction
initial begin
 q=scan(1);
 #1;r=scan(3);
 $display("TRACE types %0d %0d",q,r);
 if(q!=11||r!=32)$fatal(1,"explicit lifetime types/defaults");
end
endmodule
