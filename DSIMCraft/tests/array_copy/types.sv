`timescale 1ns/1ps
module top;
 typedef enum logic[1:0]{IDLE=0,RUN=1,DONE=2} state_t;
 typedef struct packed {logic[3:0]hi;logic[3:0]lo;} byte_t;
 state_t e[0:1],f[3:2];byte_t s[0:1];logic[7:0]v[3:2],four[0:1];bit[7:0]two[0:1];
 logic[129:0]a[0:1],b[4:3];wire[7:0]net[1:0];
 assign net[1]=v[3],net[0]=v[2];
 wire[15:0]observe_net={net[1],net[0]};
wire [3:0] observe_e={e[1],e[0]};
wire [3:0] observe_f={f[3],f[2]};
wire [15:0] observe_s={s[1],s[0]};
wire [15:0] observe_v={v[3],v[2]};
wire [15:0] observe_four={four[1],four[0]};
wire [15:0] observe_two={two[1],two[0]};
wire [259:0] observe_a={a[1],a[0]};
wire [259:0] observe_b={b[4],b[3]};
 initial begin
 a[0]=130'h200000000000000000000000000000001;a[1]=130'h100000000000000000000000000000002;b=a;
 e[0]=RUN;e[1]=DONE;f=e;s[0].hi=4'ha;s[0].lo=4'h5;s[1].hi=4'h3;s[1].lo=4'h9;v=s;
 four[0]=8'hxz;four[1]=8'ha5;two=four;four=two;
 #1 $display("TRACE types %h %h %h %h %h %h %h %h",b[4],b[3],f[3],f[2],v[3],v[2],four[0],two[1]);
 if(b[4]!==a[0]||b[3]!==a[1]||f[3]!==RUN||f[2]!==DONE||v[3]!==8'ha5||v[2]!==8'h39||four[0]!==0||two[1]!==8'ha5)$fatal(1,"types");
 four=net;a[0]='z;a[1]='x;b<=a;#1;
 $display("TRACE wide %h %h",b[4],b[3]);
 if(b[4]!=={130{1'bz}}||b[3]!=={130{1'bx}}||four[0]!==8'ha5||four[1]!==8'h39)$fatal(1,"wide");$finish;
 end
endmodule
