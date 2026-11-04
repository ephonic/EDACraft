`timescale 1ns/1ps
module top;
integer a=1,fallback=10,comb,legacy,explicit_value;
function integer f(input integer x=fallback);begin return x+1;end endfunction
function integer stable(input integer x=fallback);
 integer count=0;
 begin count++;return x+count;end
endfunction
always_comb comb=f();
always @* legacy=f();
always @* explicit_value=stable(.x(a));
initial begin
 #1 if(comb!==11||legacy!==11||explicit_value!==2)$fatal(1,"default input sensitivity startup");
 fallback=20;#1 if(comb!==21||legacy!==21||explicit_value!==2)$fatal(1,"used default only");
 a=3;#1 if(comb!==21||legacy!==21||explicit_value!==5)$fatal(1,"explicit actual sensitivity");
 $display("TRACE sensitivity complete");
end
endmodule
