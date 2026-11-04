`timescale 1ns/1ps
module top;
integer x=0,seen=0,local_seen=0;
task automatic observe(const ref integer a,output integer result);
 wait(a==3);@(a);#1;result=a;
endtask
task automatic relay(const ref integer a,output integer result);observe(a,result);endtask
task automatic parent(output integer result);
 integer local_value=0;
 fork relay(local_value,result);begin #1;local_value=3;#1;local_value=7;end join
endtask
initial begin
 fork relay(x,seen);begin #1;x<=3;#1;x<=7;end parent(local_seen);join
 $display("TRACE events %0d %0d %0d",x,seen,local_seen);
 if(x!=7||seen!=7||local_seen!=7)$fatal(1,"const ref live subscriptions");
end
endmodule
