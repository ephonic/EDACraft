`timescale 1ps/1ps
module top;int observed;typedef class B; class D extends B;function int f();return v+1;endfunction endclass class B;int v=6;endclass D d;initial begin d=new;observed=d.f();#1;$display("TRACE %0d",d.f());end
endmodule
