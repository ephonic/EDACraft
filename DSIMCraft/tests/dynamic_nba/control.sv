`timescale 1ns/1ps
module top;
integer a[],total=0,k=0,late=0;
task automatic work(input integer tag);
 a[0]<=#3 tag;#10;late++;
endtask
initial begin
 a=new[1];a[0]=0;
 for(k=1;k<=12;k++)begin
  fork work(k);begin #1;end join_any
  disable fork;#3;total+=a[0];
 end
 $display("TRACE control %0d %0d %0d %0d",total,a[0],late,k);
end
endmodule
