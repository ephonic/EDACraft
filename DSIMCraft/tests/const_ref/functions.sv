`timescale 1ns/1ps
module top;
integer x=3,q=0,r=0;
function automatic integer inspect(const ref integer a=x);return a;endfunction
function automatic integer change(const ref integer a,ref integer b);b+=2;return inspect(a);endfunction
function automatic integer classic;
 const ref integer a;
 begin return inspect(a)+1;end
endfunction
initial begin
 q=change(.b(x),.a(x));r=inspect(.a())+classic(x);
 $display("TRACE functions %0d %0d %0d",x,q,r);
 if(x!=5||q!=5||r!=11)$fatal(1,"const ref function live alias/default");
end
endmodule
