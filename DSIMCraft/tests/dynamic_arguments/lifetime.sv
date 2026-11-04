`timescale 1ns/1ps
module top;
integer a[],b[],one=0,two=0,seen=0;
task automatic work(input integer x[],output integer y[],input integer tag);
 #2;y=new[x.size()+1](x);y[x.size()]=tag;
 if(tag==1)one=x.size()*10+y.size();else two=x.size()*10+y.size();
endtask
task automatic wait_change(const ref integer x[]);
 @(x.size());seen=x.size();@(x[0]);seen+=x[0];
endtask
initial begin
 a=new[1];a[0]=4;b=new[3];foreach(b[i])b[i]=i+5;
 fork work(a,a,1);work(b,b,2);join
 $display("TRACE lifetime %0d %0d %0d %0d %0d %0d",one,two,a.size(),b.size(),a[1],b[3]);
 fork wait_change(a);begin #1;a=new[4](a);#1;a[0]=9;end join
 $display("TRACE live %0d %0d %0d",seen,a.size(),a[0]);
end
endmodule
