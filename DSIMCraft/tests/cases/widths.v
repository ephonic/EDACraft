module top;
  reg [7:0] a,b;
  reg [63:0] wide;
  wire [8:0] sum;
  wire [3:0] nibble;
  wire [15:0] pair;
  assign sum=a+b;
  assign nibble=a[7:4];
  assign pair={a,b};
  initial begin
    a=8'hff;b=8'h01;wide=64'hffffffffffffffff;
    #1 $display("TRACE sum=%h nibble=%b pair=%h wrap=%h",sum,nibble,pair,wide+64'd1);
    $finish;
  end
endmodule
