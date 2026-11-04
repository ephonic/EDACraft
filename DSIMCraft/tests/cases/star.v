module top;
  reg a,b;
  reg y;
  always @* begin
    if(a) y=b;
    else y=0;
  end
  initial begin
    a=0;b=1;
    #1 $display("TRACE y=%b",y);
    a=1;
    #1 $display("TRACE y=%b",y);
    b=0;
    #1 $display("TRACE y=%b",y);
    $finish;
  end
endmodule
