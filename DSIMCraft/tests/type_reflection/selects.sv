module top;
 int a;integer b;logic signed [3:0][7:0] x;reg[7:0] y;bit[7:0] z;
 initial begin
 $display("TRACE selects [%s] [%s] [%s] [%s] [%s] [%s]",$typename(a[0]),$typename(b[0]),$typename(x[0]),$typename(x[0][0]),$typename(y[3:1]),$typename(z[0]));
 $display("TRACE ones [%s] [%s] [%s]",$typename('1),$typename(1'b1),$typename(1'bx));
 end
endmodule
