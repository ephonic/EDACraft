`timescale 1ns/1ps
module top;
integer a,hidden,comb,legacy,void_value;
function integer value(input integer x);
 begin return x+hidden;end
endfunction
function void update(input integer x);
 begin void_value=x+hidden;end
endfunction
always_comb comb=value(a);
always @* legacy=value(a);
always_comb update(a);
initial begin
 #1 a=1;hidden=10;
 #1 if(comb!==11||legacy!==11||void_value!==11)$fatal(1,"initial inputs");
 a=2;#1 if(comb!==12||legacy!==12||void_value!==12)$fatal(1,"actual input trigger");
 hidden=20;#1 if(comb!==22||legacy!==12||void_value!==22)$fatal(1,"function body sensitivity");
 a=3;#1 if(comb!==23||legacy!==23||void_value!==23)$fatal(1,"second trigger");
 $display("TRACE sensitivity complete");
end
endmodule
