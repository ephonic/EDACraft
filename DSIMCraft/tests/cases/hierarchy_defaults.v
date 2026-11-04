module defaults #(parameter W=4)(input [W-1:0] a='1,output [W-1:0] y);
  assign y=a;
endmodule
module top(input logic floating,input [3:0] default_top=4'ha);
  reg [3:0] a;
  wire [3:0] connected,open_named,open_implicit;
  defaults c(.a(a),.y(connected));
  defaults n(.a(),.y(open_named));
  defaults i(.y(open_implicit));
  initial begin
    a=4'h0;
    #1 $display("TRACE connected=%h named=%h implicit=%h top=%h floating=%b",connected,open_named,open_implicit,default_top,floating);
    a=4'h5;
    #1 $display("TRACE connected=%h named=%h implicit=%h",connected,open_named,open_implicit);
    $finish;
  end
endmodule
