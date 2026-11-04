`timescale 1ps/1ps
module top;int observed;typedef class C;typedef C Alias;Alias c=new;class C;int v=12;endclass initial begin observed=c.v;#1;$display("TRACE %0d",c.v);end
endmodule
