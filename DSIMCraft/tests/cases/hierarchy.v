module leaf #(parameter W=4, parameter INC=1)(input [W-1:0] a, output [W-1:0] y);
  localparam [W-1:0] STEP=INC;
  assign y=a+STEP;
endmodule
module wrapper #(parameter W=4)(input [W-1:0] a, output [W-1:0] y);
  leaf #(.W(W),.INC(2)) inner(.y(y),.a(a));
endmodule
module top;
  reg [7:0] a;
  wire [3:0] y4;
  wire [7:0] y8, nested;
  leaf #(4,1) u4(a,y4);
  leaf #(.W(8),.INC(3)) u8(.a(a),.y(y8));
  wrapper #(.W(8)) wrap(.a(a),.y(nested));
  initial begin
    a=8'h0e;
    #1 $display("TRACE small=%h large=%h nested=%h",y4,y8,nested);
    a=8'hff;
    #1 $display("TRACE small=%h large=%h nested=%h",y4,y8,nested);
    $finish;
  end
endmodule
