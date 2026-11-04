`timescale 1ns/1ps
module top;
 logic signed[7:0]a[3:2],b[0:1],q[9:8];integer i;
wire [15:0] observe_a={a[3],a[2]};
wire [15:0] observe_b={b[1],b[0]};
wire [15:0] observe_q={q[9],q[8]};
 initial begin a[3]=-2;a[2]=7;b=a;q<=b;
 #1 $display("TRACE initial %h %h %h %h",b[0],b[1],q[9],q[8]);
 if(b[0]!==8'hfe||b[1]!==7||q[9]!==8'hfe||q[8]!==7)$fatal(1,"initial copy");
 a[3]=8'hxz;a[2]=8'hz1;b=a;b=b;q<=b;
 #1 $display("TRACE unknown %h %h %h %h",b[0],b[1],q[9],q[8]);
 if(b[0]!==8'hxz||b[1]!==8'hz1||q[9]!==8'hxz||q[8]!==8'hz1)$fatal(1,"unknown copy");$finish;
 end
endmodule
