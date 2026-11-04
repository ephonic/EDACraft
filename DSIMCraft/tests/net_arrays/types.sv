`timescale 1ns/1ps
module convert(input wire[129:0]a[3:2],input bit[7:0]b[0:1],output wire[129:0]q[5:6],output wire[7:0]converted0,converted1);
 assign q[5]=a[3],q[6]=a[2],converted0=b[0],converted1=b[1];
wire [259:0] observe_a={a[3],a[2]};
wire [15:0] observe_b={b[1],b[0]};
wire [259:0] observe_q={q[6],q[5]};
endmodule
module top;
 logic[129:0]d[0:1],q[0:1];wire[7:0]b[1:0];logic en;integer index;logic[129:0]sample;
 assign b[1]=en?8'hxz:8'h39,b[0]=8'h5a;
 wire[7:0]converted0,converted1;
 convert c(d,b,q,converted0,converted1);
wire [259:0] observe_d={d[1],d[0]};
wire [259:0] observe_q={q[1],q[0]};
wire [15:0] observe_b={b[1],b[0]};
 initial begin en=0;index=0;d[0]=130'h200000000000000000000000000000001;d[1]=130'h100000000000000000000000000000002;
 #1 sample=q[index];$display("TRACE wide %h %h %h %h",q[0],q[1],converted0,converted1);
 if(q[0]!==d[0]||q[1]!==d[1]||sample!==d[0]||converted0!==8'h39||converted1!==8'h5a)$fatal(1,"wide");
 en=1;d[0]='z;d[1]='x;#1 $display("TRACE conversion %h %h %h %h",q[0],q[1],converted0,converted1);
 if(q[0]!=={130{1'bz}}||q[1]!=={130{1'bx}}||converted0!==0||converted1!==8'h5a)$fatal(1,"conversion");$finish;
 end
endmodule
