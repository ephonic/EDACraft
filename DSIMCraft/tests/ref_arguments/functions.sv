`timescale 1ns/1ps
module top;
integer x=1,q=0,r=0,copied=0;
function automatic integer bump(ref integer a,ref integer b);
 a++;b+=2;return a+b;
endfunction
function automatic integer outer(ref integer a);
 integer intermediate;
 intermediate=bump(a,a);a++;return intermediate+a;
endfunction
function automatic integer mix(input integer n,ref integer a,output integer out);
 integer saved=n;
 a+=saved;out=a;return a+1;
endfunction
initial begin
 q=bump(x,x);
 r=outer(x);
 q+=mix(.out(copied),.a(x),.n(3));
 $display("TRACE functions %0d %0d %0d %0d",x,q,r,copied);
 if(x!=11||q!=20||r!=22||copied!=11)$fatal(1,"nested ref function alias/copyout");
end
endmodule
