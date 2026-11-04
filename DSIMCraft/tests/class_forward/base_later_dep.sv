`timescale 1ps/1ps
module top;int observed;typedef class B;class D extends B;endclass int g=9;class B;int v=g;endclass D d;initial begin d=new;observed=d.v;#1;$display("TRACE %0d",d.v);end
endmodule
