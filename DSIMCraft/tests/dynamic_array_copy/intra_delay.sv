`timescale 1ns/1ps
module top;
logic[7:0]a[1:0][0:1],b[1:0][0:1];integer src,dst,calls,r0,r1;
task automatic copy_wait(input integer seed,input integer ticks,output integer result);
logic[7:0]x[1:0][0:1],y[0:1];integer k;
begin x[1][0]=seed;x[1][1]=seed+1;k=1;y=#ticks x[k];result=y[0]+y[1];end
endtask
function automatic integer pick(input integer v);begin calls=calls+1;pick=v;end endfunction
initial begin calls=0;a[1][0]=7;a[1][1]=8;src=1;dst=1;b[pick(dst)]=#3 a[pick(src)];
if(b[0][0]!==7||b[0][1]!==8||b[1][0]!==8'bx||calls!==2)$fatal(1,"resume target");
copy_wait(10,2,r0);#1;if(r0!==21||r1!==41)$fatal(1,"automatic copies");
$display("TRACE intra %h %h %0d %0d %0d",b[0][0],b[0][1],calls,r0,r1);$finish;end
initial begin #1;src=0;dst=0;a[1][0]=99;copy_wait(20,3,r1);end
wire [31:0] observe_a={a[0][1],a[0][0],a[1][1],a[1][0]};
wire [31:0] observe_b={b[0][1],b[0][0],b[1][1],b[1][0]};
endmodule
