`timescale 1ns/10ps
`celldefine
module C(input A, B, output Z, Y);
  assign Z=A&B;
  assign Y=A|B;
  // Body strings/comments do not create fake paths or modules.
  initial $display("specify module FAKE endspecify endmodule");
  specify
    specparam rise=(0.004:0.005:0.006), fall=0.014, alias_delay=rise;
    (A, B *> Z, Y) = (alias_delay,fall);
    if (B == 1'b0) (A => Z) = 0.020;
    ifnone (A => Z) = 0.030;
    (posedge A => (Y +: B)) = (0.040,0.050);
    pulsestyle_ondetect Z,Y;
    noshowcancelled Z;
    $setup(B, posedge A &&& B, 0.010);
    $hold(posedge A, B, 0.020);
    $setuphold(posedge A, B, 0.010, 0.020, , , , , );
    $width(posedge A, 0.030);
  endspecify
endmodule
`endcelldefine
`timescale 10ps/1ps
module F(CP,D,Q);
  input CP,D;
  output Q;
  reg saved;
  always @(posedge CP) begin saved<=D; end
  assign Q=saved;
  specify
    (posedge CP => (Q:1'bx)) = 0;
    $recovery(negedge D, posedge CP, 0);
    $removal(negedge D, posedge CP, 0);
  endspecify
endmodule
