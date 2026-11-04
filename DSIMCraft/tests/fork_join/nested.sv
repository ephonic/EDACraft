`timescale 1ns/1ps
module top;integer a=0,b=0,c=0;
task automatic work(input integer n,output integer value);integer local_value;begin local_value=n;#n;value=local_value+10;end endtask
initial begin
fork
begin fork work(1,a);work(3,b);join c=1;end
begin #2;if(c!==0)$fatal(1,"early join");end
join
$display("TRACE nested %0d %0d %0d %0t",a,b,c,$time);$finish;end
endmodule
