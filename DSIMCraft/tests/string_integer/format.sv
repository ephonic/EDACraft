`timescale 1ns/1ps
module top;string text;int count=0;
task check(input logic[31:0] value,input string dec,hexv,oct,bin);begin
text.itoa(value);if(text!=dec)$fatal(1,"itoa");$display("TRACE dec %s",text);
text.hextoa(value);if(text!=hexv)$fatal(1,"hextoa");$display("TRACE hex %s",text);
text.octtoa(value);if(text!=oct)$fatal(1,"octtoa");$display("TRACE oct %s",text);
text.bintoa(value);if(text!=bin)$fatal(1,"bintoa");$display("TRACE bin %s",text);count++;end endtask
initial begin
check(0,"0","0","0","0");
check(1,"1","1","1","1");
check(-1,"-1","ffffffff","37777777777","11111111111111111111111111111111");
check(-2147483648,"-2147483648","80000000","20000000000","10000000000000000000000000000000");
check(2147483647,"2147483647","7fffffff","17777777777","1111111111111111111111111111111");
check(64'h100000001,"1","1","1","1");
check(32'hx,"?","?","?","xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx");
check(32'hz,"?","?","?","zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz");
check(32'h8x0f,"?","?","?","1000xxxx00001111");
check(32'b10z1,"?","?","?","10z1");
#1;$finish;end endmodule
