`timescale 1ps/1ps
module top;int observed;typedef class B; class A; B b; endclass class B; A a; endclass A x; B y; initial begin x=new;y=new;x.b=y;y.a=x;observed=x.b.a==x;#1;$display("TRACE %0d",x.b.a==x);end
endmodule
