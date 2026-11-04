`timescale 1ns/1ps
module top;
integer a[],count=0,done=0,k=0;
task automatic work(inout integer x[],input integer tag);
 x=new[x.size()+1](x);x[x.size()-1]=tag;
 #2;count+=x.size();
endtask
initial begin
 a=new[1];a[0]=7;
 for(k=0;k<12;k++)begin
  begin: cancelled
   fork work(a,99);begin #1;disable cancelled;end join
  end
  work(a,k);done++;
 end
 $display("TRACE control %0d %0d %0d %0d %0d",count,done,a.size(),a[0],a[a.size()-1]);
end
endmodule
