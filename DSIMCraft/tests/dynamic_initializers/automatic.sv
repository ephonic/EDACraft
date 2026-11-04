`timescale 1ns/1ps
module top;
integer observed=0;integer seed[]=new[2];
task automatic work(input integer n);
integer m=n+1;integer a[]=new[m],b[]=new[m+1](a),c[]=b;
a[0]=n;#1;observed+=a[0]+a.size();$display("TRACE auto %0d %0d %0d %0d %h",n,a.size(),b.size(),c.size(),b[0]);endtask
function automatic integer fold(input integer n);integer a[]=new[n];a[0]=n;return a.size()+a[0];endfunction
task automatic seeded(const ref integer source[],input integer count);
 integer local_values[]=new[count](source),copy[]=source;
 integer used=local_values.size();
 local_values[0]=count;
 #1;observed+=copy[0]+local_values[0];
 $display("TRACE seeded %0d %0d %0d %0d %0d",local_values.size(),copy.size(),local_values[0],copy[0],used);
endtask
initial begin work(2);work(4);seed[0]=7;seeded(seed,3);seed[0]=9;seeded(seed,1);$display("TRACE fn %0d %0d",fold(3),fold(5));end endmodule
