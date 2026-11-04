module top;
 bit a[2];logic[7:3] b[2];logic[1:0][3:0] c[2];
 initial $display("TRACE query %0d %0d %0d %0d %0d %0d %0d",$dimensions(a.sum()),$dimensions(b.sum()),$left(b.sum()),$right(b.sum()),$dimensions(c.sum()),$size(c.sum(),1),$size(c.sum(),2));
endmodule
