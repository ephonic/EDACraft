`timescale 1ns/1ps
module top;
reg[7:0] a=8'hff;
reg signed[7:0] s=-2;
reg[15:0] q=0,r=0;
reg signed[129:0] wide=-130'sd1,prior=0;
reg[7:0] four=8'bzzzz0101,oldfour=0;
function integer triple(input integer x);
 begin return x*3;end
endfunction
initial begin
 #1;q=++a;$display("TRACE prefix %h %h",a,q);
 a=8'hff;q=a++;$display("TRACE postfix %h %h",a,q);
 q=s++;r=++s;$display("TRACE signed %h %h %h",s,q,r);
 #1;q=--a;r=a--;$display("TRACE decrement %h %h %h",a,q,r);
 a=8'hff;q=(++a)+16'd1;$display("TRACE context %h %h",a,q);
 a=8'hfe;q=triple(a++);$display("TRACE argument %h %h",a,q);
 #1;prior=wide++;$display("TRACE wide %h %h",wide,prior);
 oldfour=four++;$display("TRACE four %b %b",four,oldfour);
 #1;$finish;
end
endmodule
