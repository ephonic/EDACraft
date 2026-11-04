`timescale 1ps/1ps
module top;int observed;class C;int v=g;endclass int g=23;C c;initial begin c=new;observed=c.v;#1;$display("TRACE %0d",c.v);end
endmodule
