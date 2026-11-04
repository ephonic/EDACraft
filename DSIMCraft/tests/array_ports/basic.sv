`timescale 1ns/1ps
module child(input logic signed[7:0] a[3:2],output logic signed[7:0]q[5:6]);
 assign q[5]=a[3]+1,q[6]=a[2]+2;
wire [15:0] observe_a={a[3],a[2]};
wire [15:0] observe_q={q[6],q[5]};
endmodule
module top;
 logic signed[7:0]a[0:1],q[9:8];child u(a,q);
wire [15:0] observe_a={a[1],a[0]};
wire [15:0] observe_q={q[9],q[8]};
initial begin
 a[0]=-3;a[1]=5;
 #1 $display("TRACE basic %h %h",q[9],q[8]);
 if(q[9]!==8'hfe||q[8]!==7)$fatal(1,"basic first");
 a[1]<=8'hxz;
 #1 $display("TRACE unknown %h %h",q[9],q[8]);
 if(q[9]!==8'hfe||q[8]!==8'hxx)$fatal(1,"basic unknown");
 a[0]=7;a[1]=8;
 #1 $display("TRACE final %h %h",q[9],q[8]);
 if(q[9]!==8||q[8]!==10)$fatal(1,"basic final");$finish;
 end
endmodule
