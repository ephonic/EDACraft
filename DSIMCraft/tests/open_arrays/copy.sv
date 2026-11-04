`timescale 1ns/1ps
module top;
integer a[5:3],seen=0;
task automatic inspect(input integer values[],output integer result);
 values[0]=99;result=values[$right(values)];
endtask
task automatic change(inout integer values[]);
 foreach(values[i])values[i]+=10;
 #2;values[1]+=20;
endtask
initial begin
 a[5]=1;a[4]=2;a[3]=3;inspect(.result(seen),.values(a));
 fork change(a);begin #1;a[4]=100;end join
 $display("TRACE copy %0d %0d %0d %0d",a[5],a[4],a[3],seen);
 if(a[5]!=11||a[4]!=32||a[3]!=13||seen!=3)$fatal(1,"unsized copy-in/out");
end
endmodule
