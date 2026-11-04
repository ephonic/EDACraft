`timescale 1ps/1ps
module grid #(parameter FLIP=0)(input [7:0] a,output [7:0] y,output [71:0] wide);
  for (genvar r=0;r<2;r=r+1) begin: row
    localparam [7:0] R=r;
    wire [7:0] ordinal=r*4+1;
    for (genvar c=0;c<4;c=c+1) begin: col
      localparam [7:0] POS=r*4+c;
      wire shadow;
      if ((r+c)%2==FLIP) begin: even
        wire shadow = a[POS];
        assign y[POS]=shadow;
      end else begin: odd
        not inv(shadow,a[POS]);
        assign y[POS]=shadow;
      end
    end
  end
  if (FLIP) begin
    assign wide = {9{a}};
  end else begin
    assign wide = {a,64'hx0123456789abcde};
  end
  for (genvar empty=2;empty<2;empty=empty+1) begin: absent
    nonexistent u();
  end
  for (genvar e=0;e<2;e=e+1) begin: empty_body end
endmodule
module top;
  reg [7:0] a,b;
  wire [7:0] x,y;
  wire [71:0] wx,wy;
  grid #(.FLIP(0)) u(a,x,wx);
  grid #(.FLIP(1)) v(b,y,wy);
  initial begin a=8'h35;#3 a=8'hc7;#3 a=8'bx1z00110;end
  initial begin b=8'h12;#4 b=8'ha9;#4 b=8'bz0x11001;end
endmodule
