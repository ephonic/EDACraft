module top;
wire [63:0] h,d,signed_value,unsized_value,unsized_x,integer_wrap,based_wrap,unsigned_max,based_signed_wrap,based_decimal_wrap; wire [31:0] pad,sample; wire [15:0] sized; wire [7:0] fill; wire [1:0] trunc; wire [11:0] padded,allz; wire [39:0] number; wire [2:0] floating;
dut u(h,d,signed_value,unsized_value,unsized_x,integer_wrap,based_wrap,unsigned_max,based_signed_wrap,based_decimal_wrap,pad,sample,sized,fill,trunc,padded,allz,number,floating);
initial begin
#1;
$display("TRACE h=%b d=%b pad=%b sized=%b fill=%b sample=%b trunc=%b padded=%b allz=%b number=%b floating=%b signed_value=%b unsized_value=%b unsized_x=%b integer_wrap=%b based_wrap=%b unsigned_max=%b based_signed_wrap=%b based_decimal_wrap=%b",h,d,pad,sized,fill,sample,trunc,padded,allz,number,floating,signed_value,unsized_value,unsized_x,integer_wrap,based_wrap,unsigned_max,based_signed_wrap,based_decimal_wrap);
$finish; end endmodule
