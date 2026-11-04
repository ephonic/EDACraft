`timescale 1ps/1ps
module top;int observed;typedef class C; C c=new; int g=23; class C;int v=g;function int get();return v;endfunction endclass initial begin observed=c.get();#1;$display("TRACE %0d",c.get());end
endmodule
