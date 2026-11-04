`timescale 1ns/1ps
module top;
integer a[],b[],fixed_values[3:1],n=3,q=0;
int c[];
initial begin
 $display("TRACE empty %0d %0d",a.size(),c.size());
 a=new[n];c=new[2];
 $display("TRACE default %0d %b %0d",a.size(),a[0],c[0]);
 a[0]=10;a[1]=20;a[2]=30;b=a;a[0]=99;
 #2;
 $display("TRACE copy %0d %0d %0d",b.size(),b[0],a[0]);
 a=new[5](b);q=a[0]+a[1]+a[2];
 $display("TRACE grow %0d %0d %b",a.size(),q,a[4]);
 a=new[1](a);a[0]++;a[-1]=123;a[99]=456;
 $display("TRACE shrink %0d %0d %b %0d",a.size(),a[0],a[99],c[99]);
 fixed_values[3]=7;fixed_values[2]=8;fixed_values[1]=9;b=new[4](fixed_values);
 $display("TRACE fixed %0d %0d %0d %0d %b",b.size(),b[0],b[1],b[2],b[3]);
 #2;a.delete();b=new[0];c.delete();
 $display("TRACE deleted %0d %0d %0d",a.size(),b.size(),c.size());
end
endmodule
