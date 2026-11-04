`timescale 1ns/1ps
module top;
 logic[129:0]a[0:1],q[3:2];integer r0,r1;
 wire[259:0]observe_a={a[1],a[0]},observe_q={q[3],q[2]};
 task automatic copy_wait(input integer seed,input integer ticks,output integer result);
 logic[7:0]a[0:1],b[3:2];
 begin a[0]=seed;a[1]=seed+1;b=#ticks a;result=b[3]+b[2];end
 endtask
 initial begin a[0]=130'h200000000000000000000000000000001;a[1]=130'h100000000000000000000000000000002;q=#3 a;
 #2;$display("TRACE intra %h %h %0d %0d",q[3],q[2],r0,r1);
 if(q[3]!==130'h200000000000000000000000000000001||q[2]!==130'h100000000000000000000000000000002||r0!==11||r1!==17)$fatal(1,"intra delay");$finish;end
 initial begin #1;a[0]='z;a[1]='x;copy_wait(8,2,r1);end
 initial copy_wait(5,4,r0);
endmodule
