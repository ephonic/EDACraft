`timescale 1ns/1ps
module top;
integer a[],observed=0,step=0;
task automatic mutate(ref integer x[]);
 x=new[2](x);x[1]=12;
 #2;x=new[3](x);x[2]=30;
 #2;x.delete();
endtask
task automatic forward(ref integer x[]);mutate(x);endtask
task automatic observe(const ref integer x[]);
 #1;observed=x[0]+x[1]+x.size();
 #2;observed+=x[2]+x.size();
 #2;observed+=x.size();
endtask
function automatic integer head(const ref integer x[]);return x.size()?x[0]:-1;endfunction
initial begin
 a=new[1];a[0]=5;
 fork forward(a);observe(a);begin #1;step=head(a);#2;step+=head(a);end join
 $display("TRACE references %0d %0d %0d",observed,step,a.size());
end
endmodule
