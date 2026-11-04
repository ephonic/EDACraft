`timescale 1ns/1ps
module top;
integer first,second,third;
reg [7:0] hold,merged;
reg [15:0] extended;
function integer accum(input integer a);
 integer state=0;
 begin state=state+a;accum=state;end
endfunction
function [7:0] sticky(input [7:0] a,input en);
 begin if(en)sticky=a;end
endfunction
function [7:0] narrow(input [7:0] a);
 begin narrow=a;end
endfunction
initial begin
 first=accum(2);second=accum(3);third=accum(-1);
 hold=sticky(8'ha5,1);hold=sticky(8'h11,0);
 extended=(8'hff+8'h1)+narrow(0);
 $display("TRACE state %0d %0d %0d %h %h",first,second,third,hold,extended);
 #1;
 first=1?accum(10):accum(1000);
 second=0?accum(1000):accum(20);
 merged=1'bx ? sticky(8'h33,1):sticky(8'h55,1);
 third=accum(0);
 $display("TRACE choice %0d %0d %0d %h",first,second,third,merged);
 #1;
 first=accum(1);second=accum(1);
 $display("TRACE retained %0d %0d",first,second);
 $finish;
end
endmodule
