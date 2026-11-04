`timescale 1ns/1ps
module top;
 logic[7:0]source[0:1],mirror[3:2],out[0:1];integer total,r0,r1;
 function automatic integer touch(input integer seed);
 logic[7:0]a[3:2],b[0:1];
 begin a[3]=seed;a[2]=seed+1;b=a;out=b;return b[0]+b[1];end
 endfunction
 task automatic copy_wait(input integer seed,input integer ticks,output integer result);
 logic[7:0]a[0:1],b[3:2];
 begin a[0]=seed;a[1]=seed+1;#ticks;b=a;result=b[3]+b[2];end
 endtask
 always_comb mirror=source;
wire [15:0] observe_source={source[1],source[0]};
wire [15:0] observe_mirror={mirror[3],mirror[2]};
wire [15:0] observe_out={out[1],out[0]};
 initial begin source[0]=1;source[1]=2;total=touch(3);copy_wait(5,4,r0);
 #1 $display("TRACE effects %0d %0d %0d %h %h %h %h",total,r0,r1,out[0],out[1],mirror[3],mirror[2]);
 if(total!==7||r0!==11||r1!==17||out[0]!==3||out[1]!==4||mirror[3]!==4||mirror[2]!==5)$fatal(1,"effects");$finish;
 end
 initial begin #1;source[0]=4;source[1]=5;copy_wait(8,2,r1);end
endmodule
