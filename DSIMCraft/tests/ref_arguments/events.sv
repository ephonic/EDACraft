`timescale 1ns/1ps
module top;
integer x=0,seen=0,local_seen=0,done=0;
task automatic observe(ref integer a,output integer captured);
 wait(a==3);@(a);captured=a;#1;a+=10;
endtask
task automatic relay(ref integer a,output integer captured);
 observe(a,captured);
endtask
task automatic parent(input integer seed,output integer out);
 integer local_value=seed;
 fork
  relay(local_value,out);
  begin #1;local_value=3;#1;local_value=7;end
 join
 done=local_value;
endtask
initial begin
 fork
  relay(x,seen);
  begin #1;x=3;#1;x=7;end
  parent(1,local_seen);
 join
 $display("TRACE events %0d %0d %0d %0d",x,seen,local_seen,done);
 if(x!=17||seen!=7||local_seen!=7||done!=17)$fatal(1,"ref waits and caller automatic frame");
end
endmodule
