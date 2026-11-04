module decode(input [3:0] a,input [3:0] label,input [7:0] data,output reg [7:0] y);
  reg [7:0] i;
  always @* begin
    y=0;
    for(i=0;i<3;i=i+8'd1) begin
      case(a)
        label: y=y+data;
        4'hf: y=y+8'd1;
        default: y=y+8'd2;
      endcase
    end
  end
endmodule
module top;
  reg [3:0] a,label;
  reg [7:0] data;
  wire [7:0] y;
  decode u(a,label,data,y);
  initial begin
    a=2; label=2; data=4;
    #1 $display("TRACE y=%0d",y);
    data=5;
    #1 $display("TRACE y=%0d",y);
    label=3;
    #1 $display("TRACE y=%0d",y);
    a=15;
    #1 $display("TRACE y=%0d",y);
    $finish;
  end
endmodule
