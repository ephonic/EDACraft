`timescale 1ns/1ps
module choices #(parameter MODE=0)(input [7:0] a, output [7:0] y, output [3:0] bits);
  genvar i;
  generate
    if (MODE==0) begin: zero
      assign y=a;
    end else if (MODE==1) begin: one
      assign y=~a;
    end else begin: two
      assign y=a^8'ha5;
    end
    for (i=3;i>=0;i=i-1) begin: reverse
      localparam [7:0] I=i;
      assign bits[i]=a[I];
    end
    if(0) begin: unselected missing no();end
    if(1) begin
      wire [7:0] echo=a;
    end
    case(MODE)
      0: begin: mode0 wire [7:0] m=a; end
      1: begin: mode1 wire [7:0] m=~a; end
      default: begin: other wire [7:0] m=a^8'ha5; end
    endcase
    for(i=1;i<1;i=i+1) begin: no_iterations end
  endgenerate
endmodule
module top;
  reg [7:0] a;
  wire [7:0] y0,y1,y2;
  wire [3:0] b0,b1,b2;
  choices #(.MODE(0)) u(a,y0,b0);
  choices #(.MODE(1)) v(a,y1,b1);
  choices #(.MODE(2)) w(a,y2,b2);
  initial begin
    a=8'h39;#1 $display("TRACE y=%h %h %h b=%h %h %h",y0,y1,y2,b0,b1,b2);
    a=8'bxz0110z1;#1 $display("TRACE y=%b %b %b b=%b",y0,y1,y2,b2);
    $finish;
  end
endmodule
