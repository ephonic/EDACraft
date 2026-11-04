module top;
  reg a,b,en;
  wire n,y,z,bus;
  and g1(n,a,b);
  not g2(y,n);
  xor g3(z,a,b);
  assign bus=en ? a : 1'bz;
  assign bus=b;
  initial begin
    a=0;b=0;en=0;
    #1 $display("TRACE n=%b y=%b z=%b bus=%b",n,y,z,bus);
    a=1;b=0;en=1;
    #1 $display("TRACE n=%b y=%b z=%b bus=%b",n,y,z,bus);
    b=1;
    #1 $display("TRACE n=%b y=%b z=%b bus=%b",n,y,z,bus);
    a=1'bz;en=0;
    #1 $display("TRACE n=%b y=%b z=%b bus=%b",n,y,z,bus);
    $finish;
  end
endmodule
