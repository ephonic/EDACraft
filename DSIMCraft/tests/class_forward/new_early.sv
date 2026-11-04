`timescale 1ps/1ps
module top;int observed;typedef class C; C c=new; initial begin observed=c.get();#1;$display("TRACE %0d",c.get());end class C;int v=17;function int get();return v;endfunction endclass
endmodule
