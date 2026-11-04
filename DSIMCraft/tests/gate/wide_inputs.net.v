module back(input wire [7:4] i,output wire [3:0] seen);
assign i=4'bzz10; assign seen=i;
endmodule
module single(input wire [9:9] a,output wire y); assign y=a; endmodule
module asc(input [1:2] a,output [9:8] y); assign y=a; endmodule
module dut(input a,b,output [3:0] plain,cat,sp,sc,sw,
output [1:0] short_bus,ascending,output one,output [3:0] open);
assign plain={a,b,a,b}; assign cat={a,b,a,b}; assign short_bus={a,b};
back p(.i(plain),.seen(sp));
back c(.i({cat}),.seen(sc));
back w(.i(short_bus),.seen(sw));
back z(.i(),.seen(open));
single s(.a({a}),.y(one)); asc t(.a({a,b}),.y(ascending));
endmodule
