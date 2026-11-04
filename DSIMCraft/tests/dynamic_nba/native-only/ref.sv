`timescale 1ns/1ps
module top;
integer a[],total=0;
task automatic issue(ref integer x[],input integer tag);x[0]<=#3 tag;endtask
task automatic frame(input integer tag);
 integer local_array[];
 local_array=new[1];local_array[0]=0;issue(local_array,tag);
 #4;total+=local_array[0];
endtask
initial begin
 fork frame(10);frame(20);join
 a=new[1];a[0]=1;issue(a,7);#1;a=new[2](a);#3;
 $display("TRACE native ref %0d %0d",total,a[0]);
 if(total!=30||a[0]!=1)$fatal(1,"reference NBA capture");
end
endmodule
