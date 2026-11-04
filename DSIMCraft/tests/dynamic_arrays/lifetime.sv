`timescale 1ns/1ps
module top;
integer a[],one=0,two=0,seen=0,total=0,k=0;
function automatic integer fold(input integer n);
 integer local_values[],sum=0;
 assert(local_values.size()==0);
 local_values=new[n];foreach(local_values[i])begin local_values[i]=i+1;sum+=local_values[i];end
 return sum;
endfunction
task automatic work(input integer tag,input integer count);
 integer values[];
 if(values.size()!=0)$fatal(1,"stale automatic dynamic storage");
 values=new[count];foreach(values[i])values[i]=tag*10+i;
 #2;
 if(tag==1)one=values[0]+values[count-1];else two=values[0]+values[count-1];
endtask
initial begin
 for(k=1;k<=3;k++)total+=fold(k);
 fork work(1,2);work(2,4);join
 for(k=1;k<=3;k++)work(1,k);
 $display("TRACE automatic %0d %0d %0d",one,two,total);
 a=new[1];a[0]=0;
 fork
  begin @(a[0]);seen=a[0];@(a.size());seen+=a.size();end
  begin #1;a[0]=7;#1;a=new[3](a);end
 join
 $display("TRACE events %0d %0d %0d",seen,a.size(),a[0]);
end
endmodule
