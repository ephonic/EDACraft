`timescale 1ns/1ps
module pad(inout wire[3:0]p[3:2],input logic en);
 assign p[3]=en?4'ha:4'hz;
 assign p[2]=en?4'h5:4'hz;
wire [7:0] observe_p={p[3],p[2]};
endmodule
module top;
 tri[3:0]p[0:1];logic en,drive;integer i;logic[3:0]sample;
 pad u(p,en);
 wire buffered;buf g(buffered,p[1][0]);
 assign p[0]=drive?4'h5:4'hz;
 assign p[1]=drive?4'h5:4'hz;
wire [7:0] observe_p={p[1],p[0]};
 initial begin en=1;drive=0;i=0;
 #1 sample=p[i];$display("TRACE pad %h %h %h",p[0],p[1],sample);
 if(p[0]!==4'ha||p[1]!==4'h5||sample!==4'ha)$fatal(1,"pad");
 drive=1;i=1;#1 sample=p[i];$display("TRACE clash %h %h %h",p[0],p[1],sample);
 if(p[0]!==4'bxxxx||p[1]!==4'h5||sample!==4'h5)$fatal(1,"clash");
 en=0;drive=0;#1 i=4;sample=p[i];$display("TRACE off %h %h %h",p[0],p[1],sample);
 if(p[0]!==4'hz||p[1]!==4'hz||sample!==4'hx)$fatal(1,"off");$finish;
 end
endmodule
