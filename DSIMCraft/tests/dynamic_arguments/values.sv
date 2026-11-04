`timescale 1ns/1ps
module top;
integer a[],b[],c[],entry=0,returned=0,k=0;
task automatic copy_values(input integer x[],output integer y[],inout integer z[]);
 entry=x.size()*100+z.size();
 #2;y=new[x.size()+1](x);y[x.size()]=50;
 z=new[z.size()+1](z);z[z.size()-1]=x[0];
 x.delete();returned=y.size()*100+z.size();
endtask
initial begin
 a=new[2];a[0]=7;a[1]=8;b=new[1];b[0]=99;c=new[1];c[0]=3;
 fork copy_values(a,b,c);begin #1;a=new[4](a);a[0]=20;c[0]=88;end join
 $display("TRACE copied %0d %0d %0d %0d %0d %0d %0d %0d",entry,returned,a.size(),a[0],b.size(),b[0],c[0],c[1]);
 for(k=0;k<3;k++)begin a=new[k];if(k>0)a[0]=k;copy_values(a,b,c);$display("TRACE varying %0d %0d %0d %0d",k,b.size(),c.size(),$bits(b));end
end
endmodule
