`timescale 1ns/1ps
module top;
integer a[],b[],one=0,two=0,total=0,k=0;
task automatic work(inout integer x[],input integer tag);
 x[0]<=#1 tag;#2;
 if(tag==10)one=x[0];else two=x[0];
endtask
task automatic abandon(input integer tag);
 integer x[];
 x=new[1];x[0]=0;x[0]<=#4 tag;
 #1;total+=x[0];
 if(x[0]!=0)$fatal(1,"pending NBA leaked into a reused activation");
endtask
initial begin
 a=new[1];a[0]=1;b=new[1];b[0]=2;
 fork work(a,10);work(b,20);join
 for(k=1;k<=12;k++)abandon(k);
 $display("TRACE lifetime %0d %0d %0d %0d %0d %0d",a[0],b[0],one,two,total,k);
end
endmodule
