`timescale 1ns/1ps
module top;
 string source="abc",other="xyz";integer changes=0;
 task automatic change(ref string s,input integer position,input byte value);
  #1;s[position]=value;
 endtask
 task automatic observe(const ref string s,output byte value);value=s[1];endtask
 byte captured=0;
 always @(source)changes=changes+1;
 initial begin
  #0.5;change(source,1,8'h51);observe(source,captured);
  $display("TRACE refs [%s] %h",source,captured);
  #1;$display("TRACE sensitivity %0d",changes);$finish;
 end
 initial change(other,2,8'h4b);
endmodule
