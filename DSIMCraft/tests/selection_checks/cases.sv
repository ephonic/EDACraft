`timescale 1ns/1ps
module top;
logic[3:0] x=1;logic[128:0] wide=0;integer q=0;
initial begin
 #1;unique case(x) 1,1:q=1;2:q=2;default:q=3;endcase
 if(q!==1)$fatal(1,"same item is not overlap");
 #1;unique casez(x) 4'b0???:q=4;4'b???1:q=5;default:q=6;endcase // report overlap 2000
 if(q!==4)$fatal(1,"casez first branch");
 #1;x=8;priority casex(x) 4'b1xxx:q=7;4'bxxxx:q=8;endcase
 if(q!==7)$fatal(1,"priority casex");
 #1;unique0 case(x) 0:q=9;1:q=10;endcase
 unique case(x) 0:q=9;1:q=10;endcase // report no-match 4000
 priority case(x) inside [0:2]:q=9;[3:7]:q=10;endcase // report no-match 4000
 #1;x=3;unique case(x) inside [1:4]:q=11;[3:8]:q=12;endcase // report overlap 5000
 if(q!==11)$fatal(1,"inside first branch");
 #1;wide=129'h100000000000000000000000000000001;
 unique case(wide) 129'h100000000000000000000000000000001:q=13;129'h1:q=14;default:q=15;endcase
 if(q!==13)$fatal(1,"wide case");
 #1;$display("TRACE cases %0d",q);
end
endmodule
