`timescale 1ns/1ps
module convert #(parameter W=130)(input logic signed[W-1:0]a[2:1],output bit[W-1:0]b[4:5],output logic signed[W-1:0]q[8:9]);
 assign #1 b[4]=a[2],b[5]=a[1];assign q[8]=a[2],q[9]=a[1];
wire [259:0] observe_a={a[2],a[1]};
wire [259:0] observe_b={b[5],b[4]};
wire [259:0] observe_q={q[9],q[8]};
endmodule
module top;
 logic signed[129:0]d[0:1],q[0:1];bit[129:0]b[7:6];convert #(130)c(d,b,q);
wire [259:0] observe_d={d[1],d[0]};
wire [259:0] observe_b={b[7],b[6]};
wire [259:0] observe_q={q[1],q[0]};
initial begin
 d[0]=-130'sd3;d[1]=130'h200000000000000000000000000000005;
 #2 $display("TRACE types %h %h %h %h",q[0],b[7],q[1],b[6]);
 if(q[0]!==-130'sd3||b[7]!==-130'sd3||q[1]!==d[1]||b[6]!==d[1])$fatal(1,"types first");
 d[0]='z;d[1]=130'h123456789abcdef0123456789abcdef01;
 #2 $display("TRACE types %h %h %h %h",q[0],b[7],q[1],b[6]);
 if(q[0]!==130'bz||b[7]!==0||q[1]!==d[1]||b[6]!==d[1])$fatal(1,"types final");$finish;
 end
endmodule
