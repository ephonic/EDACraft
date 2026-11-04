`timescale 1ns/1ps
module top;
logic[7:0]a[1:0][0:1],b[0:1][1:0];integer calls;
function automatic integer pick(input integer v);begin calls=calls*10+v;pick=v;end endfunction
initial begin calls=0;a[1][0]=7;a[1][1]=8;b[pick(0)]<=#(pick(2)) a[pick(1)];
#3;if(calls!==210||b[0][1]!==7||b[0][0]!==8)$fatal(1,"single evaluation");
$display("TRACE effects %0d %h %h",calls,b[0][1],b[0][0]);$finish;end
wire [31:0] observe_a={a[0][1],a[0][0],a[1][1],a[1][0]};
wire [31:0] observe_b={b[1][0],b[1][1],b[0][0],b[0][1]};
endmodule
