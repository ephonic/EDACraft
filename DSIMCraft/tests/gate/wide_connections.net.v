module lane(input [12:9] x,output [5:2] y);
assign y={x[10:9],x[12:11]};
endmodule
module wrap(input [3:0] a,output [9:6] y);
lane u({a[0],a[3:1]},y);
endmodule
module dut(input [7:4] a,input [3:0] b,output [15:0] y);
tri [2:5] ascending; wire [31:0] wide; wire [3:0] h;
assign ascending={a[5:4],b[3:2]};
wrap w(.a({a[7:6],b[1:0]}),.y(h));
assign wide={2{{a,b}}};
assign y={ascending[2:5],h,wide[7:4],wide[27:24]};
endmodule
