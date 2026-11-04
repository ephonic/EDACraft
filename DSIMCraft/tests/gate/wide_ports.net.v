module probe(input [5:2] i,output [8:5] o,output [3:0] seen);
assign o=i; assign seen=o;
endmodule
module link(inout [6:3] io,output [3:0] seen);
assign io=4'bz1z0; assign seen=io;
endmodule
module dut(input a,b,inout [3:0] bus,
output [3:0] direct,cat,rd,rc,rw,trunc,fill,narrow,opened,ri,leaf,
output [5:0] wide,output tied);
probe d(.i({a,b}),.o(direct),.seen(rd));
probe c(.i({a,b}),.o({cat}),.seen(rc));
probe w(.i({a,b}),.o(wide),.seen(rw));
probe t(.i({1'b1,1'b0,a,b,a,b}),.o(trunc));
probe f(.i('1),.o(fill));
probe n(.i(1'b1),.o(narrow));
probe p(.i({a,b}),.o(),.seen(opened));
assign direct=4'b0011; assign cat=4'b0011; assign wide=6'b110011;
link l(.io({bus[0],bus[2:1],bus[3]}),.seen(ri));
wire \g/__dsim_pin_Y ; assign \g/__dsim_pin_Y =1'b1;
INV g(.A({a,b}),.Y(leaf));
INV r(.A(b),.Y({tied,tied}));
endmodule
