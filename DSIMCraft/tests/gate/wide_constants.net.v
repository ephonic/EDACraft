module empty(input [2:0] a,output [2:0] y); endmodule
module dut(output [63:0] h,d,signed_value,unsized_value,unsized_x,integer_wrap,based_wrap,unsigned_max,based_signed_wrap,based_decimal_wrap,output [31:0] pad,sample,
output [15:0] sized,output [7:0] fill,output [1:0] trunc,
output [11:0] padded,allz,output [39:0] number,output [2:0] floating);
wire [1023:0] wide;
assign h=64'h80ff_0001_xz0f_7a21;
assign d=64'd18446744073709551615;
assign signed_value=4'sb1010; assign unsized_value=4294967296; assign unsized_x='hx;
assign integer_wrap=2147483648; assign based_wrap='h100000000; assign unsigned_max='hffffffff;
assign based_signed_wrap='sd4294967296; assign based_decimal_wrap='d4294967296;
assign pad={8'hx,8'hz,8'b1,8'o7};
assign sized={1'b1,3'b101,12'd1025};
assign fill='x;
assign wide={32{32'hca_fe_xz01}};
assign sample={wide[1023:1016],wide[19:0],wide[31:28]};
assign trunc=4'b1xz0; assign padded=8'hz; assign allz='z; assign number=1;
empty u(.a(3'b101),.y(floating));
endmodule
