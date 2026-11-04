`timescale 1ns/1ps
module top;
integer x[0:1],seen=0,local_seen=0,done=0,source[0:1];
task automatic observe(ref integer a[2:1],output integer captured);
 wait(a[2]==3);@(a[1]);captured=a[1];#1;a[2]+=10;
endtask
task automatic relay(ref integer a[4:5],output integer captured);observe(a,captured);endtask
task automatic parent(input integer seed,output integer out);
 integer local_value[0:1];local_value[0]=seed;local_value[1]=0;
 fork relay(local_value,out);begin #1;local_value[0]=3;#1;local_value[1]=7;end join
 done=local_value[0];
endtask
function automatic integer total(input integer a[0:1]);return a[0]+a[1];endfunction
initial begin
 x[0]=0;x[1]=0;source[0]=1;source[1]=2;
 fork
  relay(x,seen);
  begin #1;x[0]<=3;#1;x[1]<=7;end
  parent(1,local_seen);
 join
 $display("TRACE events %0d %0d %0d %0d",x[0],seen,local_seen,done);
 if(x[0]!=13||seen!=7||local_seen!=7||done!=13)$fatal(1,"array reference event frames");
end
initial begin @(total(source));if(total(source)!=7)$fatal(1,"array event function");end
initial begin #2;source[1]=6;end
endmodule
