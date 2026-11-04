`timescale 1ns/1ps
module top;
integer a[2:1],source[0:1],seen=0,event_seen=0;
task automatic observe(input integer values[],output integer result);
 fork
  begin wait(values[0]==3);@(values[1]);#1;result=values[1];end
  begin #1;values[0]=3;#1;values[1]=7;end
 join
endtask
task automatic relay(input integer values[],output integer result);observe(values,result);endtask
function automatic integer sum(input integer x[0:1]);return x[0]+x[1];endfunction
initial begin
 a[2]=0;a[1]=0;source[0]=1;source[1]=2;
 fork relay(a,seen);begin #1;a[2]=99;end join
 $display("TRACE events %0d %0d %0d",a[2],seen,event_seen);
 if(a[2]!=99||seen!=7||event_seen!=7)$fatal(1,"unsized event storage");
end
initial begin @(sum(source));event_seen=sum(source);end
initial begin #2;source[1]=6;end
endmodule
