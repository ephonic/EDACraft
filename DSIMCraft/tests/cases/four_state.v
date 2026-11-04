module top;
  reg [3:0] a;
  reg [3:0] b;
  reg sel;
  wire [3:0] x,y,z;
  assign x=a & b, y=a | b, z=sel ? a : b;
  initial begin
    a=4'b10xz; b=4'b1010; sel=1'bx;
    #1 $display("TRACE a=%b and=%b or=%b mux=%b eq=%b case=%b",a,x,y,z,a==b,a===b);
    a=4'bzzzz; b=4'b0000; sel=1;
    #1 $display("TRACE and=%b or=%b mux=%b",x,y,z);
    $finish;
  end
endmodule
