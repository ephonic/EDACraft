module top;
 parameter N=7;
 reg [1:0] v=2'bxz;
 wire [6:0] a={{N{1'b1}}};
 wire [6:0] b={N{{1{1'bx}}}};
 wire [27:0] c={N{{2{v}}}};
 initial begin #1;$display("TRACE replication %b %b %b",a,b,c);
  v=2'b10;#1;$display("TRACE changed %b",c);$finish;end
endmodule
