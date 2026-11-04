`timescale 1ns/1ps
module top;
integer a[],b[],c[],d[],e[],f[],g[],h[],j[],self[];
integer idx=0, rhs=10;
task automatic values(inout integer x[]);x[0]<=#4 90;endtask
initial begin
 a=new[1];a[0]=1;a[0]<=#4 rhs;
 b=new[1];b[0]=2;b[0]<=#4 20;
 c=new[1];c[0]=3;c[0]<=#4 30;
 d=new[1];d[0]=4;d[idx]<=#4 40;
 e=new[1];e[0]=5;e[0]<=#4 50;
 f=new[1];f[0]=6;f[0]<=#4 60;
 h=new[1];h[0]=8;h[0]<=#4 80;j=new[1];j[0]=9;j[0]<=#4 90;
 self=new[1];self[0]=8;self[0]<=#4 81;
 g=new[1];g[0]=7;values(g);
 #1;rhs=99;idx=2;
 a=new[2](a);b.delete();b=new[1];b[0]=22;c=new[3](c);
 d=new[3](d);e=new[1](e);f=new[1];f[0]=66;h=f;j=a;self=self;
 #4;$display("TRACE targets %0d %0d %b %0d %0d %0d %0d %0d %0d %0d %0d",a[0],b[0],c[2],d[0],d[2],e[0],f[0],g[0],h[0],j[0],self[0]);
end
endmodule
