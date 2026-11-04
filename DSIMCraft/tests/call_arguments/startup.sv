`timescale 1ns/1ps
module top;
integer a=1,b=2,p=0,q=0,r=0,s=0;
logic clk=1,zero=0;
integer pos,neg,ff;
function integer f(input integer x);begin return x+b;end endfunction
always @* p=a;
always @* q=f(a);
always @(a) r=a;
always @(a or b) s=a+b;
initial @(posedge clk) pos=7;
initial @(negedge zero) neg=8;
always_ff @(posedge clk) ff=9;
initial begin
 #1 if(p!==1||q!==3||r!==1||s!==3||pos!==32'bx||neg!==32'bx||ff!==9)$fatal(1,"declaration events");
 a=4;b=5;clk=0;zero=1;#1 if(p!==4||q!==9||r!==4||s!==9)$fatal(1,"rearmed event controls");
 clk=1;zero=0;#1 if(pos!==7||neg!==8||ff!==9)$fatal(1,"initial event wait");
 $display("TRACE startup complete");
end
endmodule
