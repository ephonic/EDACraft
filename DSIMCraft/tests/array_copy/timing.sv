`timescale 1ns/1ps
module top;
 logic[7:0]a[0:1],b[3:2],c[5:4],d[0:1];logic clk;integer ticks;logic[7:0]stim[0:1],pipe[0:1];integer k;
 always_ff @(posedge clk)d<=a;
wire [15:0] observe_a={a[1],a[0]};
wire [15:0] observe_b={b[3],b[2]};
wire [15:0] observe_c={c[5],c[4]};
wire [15:0] observe_d={d[1],d[0]};
 initial begin a[0]=1;a[1]=2;clk=0;ticks=2;b<=#ticks a;#3;c=a;
 #2 $display("TRACE sampled %h %h %h %h %h %h %h %h",b[3],b[2],c[5],c[4],d[0],d[1],pipe[0],pipe[1]);
 if(b[3]!==1||b[2]!==2||c[5]!==8'ha5||c[4]!==8'h39||d[0]!==8'ha5||d[1]!==8'h39||pipe[0]!==30||pipe[1]!==31)$fatal(1,"delay sample");$finish;
 end
 wire[15:0]observe_stim={stim[1],stim[0]},observe_pipe={pipe[1],pipe[0]};
 initial begin stim[0]=10;stim[1]=11;for(k=0;k<3;k=k+1)begin pipe<=#2 stim;#1;stim[0]=stim[0]+10;stim[1]=stim[1]+10;end end
 initial begin #1;a[0]=8'ha5;a[1]=8'h39;ticks=7;clk=1;#1;clk=0;end
endmodule
