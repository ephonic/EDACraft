`timescale 1ps/1ps
module primitive_leaf #(parameter D=0)(input a,b,output [3:0] y);
  // This grouped, unnamed expression was previously rejected as a dropped gate.
  and (y[0],a&b);
  and #D (y[1],a,b), named(y[2],a,b);
  not #(1,2) (y[3],a);
endmodule
module primitive_wrap #(parameter D=0)(input a,b,output [3:0] y);
  primitive_leaf #(.D(D)) u(a,b,y);
endmodule
module top;
  reg a,b;
  wire [3:0] slow_value,fast_value;
  primitive_wrap #(.D(3)) slow(a,b,slow_value);
  primitive_wrap #(.D(1)) fast(a,b,fast_value);
  initial begin
    a=0;b=0;
    #5 $display("TRACE slow=%b fast=%b",slow_value,fast_value);
    a=1;b=1;
    #5 $display("TRACE slow=%b fast=%b",slow_value,fast_value);
    b=0;
    #5 $display("TRACE slow=%b fast=%b",slow_value,fast_value);
    a=1'bx;b=1;
    #5 $display("TRACE slow=%b fast=%b",slow_value,fast_value);
    a=0;b=1'bz;
    #5 $display("TRACE slow=%b fast=%b",slow_value,fast_value);
    $finish;
  end
endmodule
