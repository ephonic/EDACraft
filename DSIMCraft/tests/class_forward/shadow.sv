`timescale 1ps/1ps
module top;int observed;class C;int v=1;endclass class Outer;typedef class C;class C;int v=2;endclass C c;endclass C c;Outer o;initial begin c=new;o=new;o.c=new;observed=c.v+o.c.v;#1;$display("TRACE %0d %0d",c.v,o.c.v);end
endmodule
