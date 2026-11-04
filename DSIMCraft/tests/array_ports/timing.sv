`timescale 1ns/1ps
module delayed(input bit[7:0]a[0:1],output logic[7:0]q[3:2]);
 always @* q[3]<=#2 a[0]+1;
 assign #1 q[2]=a[1]+2;
wire [15:0] observe_a={a[1],a[0]};
wire [15:0] observe_q={q[3],q[2]};
endmodule
module top;
 logic[7:0]d[0:1],q[5:6];delayed c(d,q);
wire [15:0] observe_d={d[1],d[0]};
wire [15:0] observe_q={q[6],q[5]};
initial begin
 d[0]=1;d[1]=1;
 #0.5 $display("TRACE pending %h %h",q[5],q[6]);
 #0.5 d[0]=4;d[1]=4;
 #1 d[0]=7;d[1]=7;
 #1.5 $display("TRACE sampled %h %h",q[5],q[6]);
 if(q[5]!==5||q[6]!==9)$fatal(1,"timing sampled");
 #0.5 d[0]=8'hxz;d[1]=8'hxz;
 #2.5 $display("TRACE final %h %h",q[5],q[6]);
 if(q[5]!==1||q[6]!==2)$fatal(1,"timing final");$finish;
 end
endmodule
