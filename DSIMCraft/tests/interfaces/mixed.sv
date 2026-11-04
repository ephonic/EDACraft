`timescale 1ns/1ps
interface mixed_if;
 logic[7:0] value=0;
 modport rw(output value);
endinterface
module fill(input logic[7:0] v,mixed_if.rw a,b,output logic valid);
 initial begin valid=0;#1;a.value=v;b.value=v+1;valid=1;end
endmodule
module plain(input logic go,mixed_if a,output logic[7:0] q,mixed_if b);
 always @* q=go?a.value+b.value:0;
endmodule
module top;
 mixed_if a();mixed_if b();wire valid;wire[7:0] result;
 fill f(.v(8'h21),.a(a),.b(b),.valid(valid));plain p(valid,a,result,b);
 initial begin #1.5;if(a.value!==8'h21||b.value!==8'h22||result!==8'h43)$fatal(1,"FAIL mixed");
 $display("TRACE mixed %h %h %h",a.value,b.value,result);#1;$finish;end
endmodule
