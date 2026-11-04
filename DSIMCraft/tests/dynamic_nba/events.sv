`timescale 1ns/1ps
module top;
event e;logic clk=0;integer a[],b[],c[],n=2,phase=0,q=0;
initial begin
 a=new[4];foreach(a[i])a[i]=0;b=new[1];b[0]=1;
 a[0]<=@e 11;a[1]<=repeat(n)@(posedge clk)22;
 a[2]<=repeat(0)@(posedge clk)33;a[3]<=@(posedge clk iff n==1)44;
 b[0]<=@e 99;c[0]<=@e 77;c=new[1];c[0]=2;n=1;b=new[2](b);
 #0;phase=a[2];
 #2;q=a[0]+a[1]+a[2]+a[3];$display("TRACE first %0d %0d %0d %0d %0d %0d %0d",a[0],a[1],a[2],a[3],b[0],c[0],phase);
 #2;q=a[0]+a[1]+a[2]+a[3];$display("TRACE second %0d %0d",a[1],q);
end
initial begin #1;->e;clk=1;#1;clk=0;#1;clk=1;end
endmodule
