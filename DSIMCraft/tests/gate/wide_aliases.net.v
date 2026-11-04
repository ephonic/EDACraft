module probe(input [3:0] d,output [3:0] y,seen);
assign y=d; assign seen=y;
endmodule
module dut(input [3:0] d,output [3:0] perm,ps,repeat_net,rs,
output [1:0] left,right,output [3:0] cross_seen);
assign perm=4'b1111; assign repeat_net=4'b1111;
assign left=2'b01; assign right=2'b10;
probe p(.d(d),.y({perm[0],perm[3:1]}),.seen(ps));
probe r(.d(d),.y({repeat_net[0],repeat_net[0],repeat_net[0],repeat_net[0]}),.seen(rs));
probe c(.d(d),.y({left,right}),.seen(cross_seen));
endmodule
