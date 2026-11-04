`timescale 1ns/1ps
module top;
string s="abc";int k=0;logic [31:0] x='x;logic [7:0] c;
initial begin
 $display("TRACE unknown %h %h",s[x],s.getc(x));
 s[x]=8'h51;$display("TRACE unknown_write [%s]",s);
 s[1]=8'h00;$display("TRACE zero_write [%s]",s);
 s[1]=8'hxx;$display("TRACE x_write [%s]",s);
 s[1]=8'b01x00001;$display("TRACE partial_write [%s]",s);
 s[k++]=8'h41+k;$display("TRACE order [%s] %0d",s,k);
 #1;$finish;end endmodule
