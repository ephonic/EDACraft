`timescale 1ps/1ps
module top;
 class B; int n=11; endclass
 class D extends B; int k=22; endclass
 class E extends B; endclass
 class U; endclass
 B b; D d, keep; E e; U u; int ok;
 typedef enum logic[3:0] {A=1,C=3,X=4'bx010,Z=4'bz011} ET;
 ET value;
 initial begin
 d=new;keep=d;b=d;e=new;u=new;
 ok=$cast(d,b);$display("TRACE good %0d %0d",ok,d.k);
 b=e;ok=$cast(d,b);$display("TRACE fail %0d %0d",ok,d==keep);
 b=null;ok=$cast(d,b);$display("TRACE null %0d %0d",ok,d==null);
 ok=$cast(d,null);$display("TRACE literal %0d %0d",ok,d==null);
 ok=$cast(d,u);$display("TRACE unrelated %0d",ok);
 value=A;ok=$cast(value,8'h13);$display("TRACE trunc %0d %b",ok,value);
 ok=$cast(value,4'bx010);$display("TRACE x %0d %b",ok,value);
 ok=$cast(value,4'bz011);$display("TRACE z %0d %b",ok,value);
 ok=$cast(value,4'b1111);$display("TRACE enumfail %0d %b",ok,value);
 #1;$finish;
 end
endmodule
