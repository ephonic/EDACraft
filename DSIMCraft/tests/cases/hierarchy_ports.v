module legacy(a,y,unused);
  parameter W=4;
  input [W-1:0] a;
  output [W-1:0] y;
  reg [W-1:0] y;
  output unused;
  always @(a) y<=a;
endmodule
module open_input(input [3:0] a, output [3:0] y);
  assign y=a;
endmodule
module variable_input(input logic [3:0] a,output [3:0] y);
  assign y=a;
endmodule
module constant_source(output [3:0] y);
  assign y=4'hb;
endmodule
module top;
  reg [7:0] a;
  wire [7:0] y;
  wire [3:0] floating,expr_y,var_y,constant_y,select_y,concat_y,open_var_y;
  legacy #(4) old(.y(y),.a(a),.unused());
  open_input floating_inst(.y(floating));
  open_input expression_inst(.a(a ^ 8'h35),.y(expr_y));
  variable_input var_inst(.a(a),.y(var_y));
  open_input selected_inst(.a(a[7:4]),.y(select_y));
  open_input concat_inst(.a({a[1:0],a[7:6]}),.y(concat_y));
  variable_input open_var(.y(open_var_y));
  constant_source const_inst(.y(constant_y));
  initial begin
    a=8'hac;
    #1 $display("TRACE y=%h open=%b expr=%h var=%h const=%h select=%h concat=%h open_var=%b",y,floating,expr_y,var_y,constant_y,select_y,concat_y,open_var_y);
    a=8'hf3;
    #1 $display("TRACE y=%h open=%b expr=%h var=%h",y,floating,expr_y,var_y);
    $finish;
  end
endmodule
