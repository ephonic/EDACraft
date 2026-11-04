`timescale 1ns/1ps
module top;
  wire [3:0] a, b, c;
  genvar i;
  generate
    for (i = 0; i < 4; i++) begin : postfix
      assign a[i] = (i & 1);
    end
    for (genvar j = 0; j < 4; ++j) begin : prefix
      assign b[j] = (j & 1);
    end
    for (genvar k = 3; k >= 0; k--) begin : decrement
      assign c[k] = (k & 1);
    end
  endgenerate
  initial begin
    #1;
    if (a !== 4'ha || b !== 4'ha || c !== 4'ha) $fatal(1, "genvar increment");
    $display("TRACE genvar a=%h b=%h c=%h", a, b, c);
    $finish;
  end
endmodule
