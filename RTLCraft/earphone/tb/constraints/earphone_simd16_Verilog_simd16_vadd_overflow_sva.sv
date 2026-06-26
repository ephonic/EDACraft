// Auto-generated from SpecIR constraint SIMD16_VADD_OVERFLOW
module simd16_vadd_overflow_assertions (
    input clk,
    input rst_n,
    input [255:0] vsrc0,
    input [255:0] vsrc1,
    input [255:0] vdst,
    input start,
    input [4:0] op
);
    // Check one representative lane (lane 0); replicate for 0..15 as needed
    wire [15:0] a0 = vsrc0[15:0];
    wire [15:0] b0 = vsrc1[15:0];
    wire [15:0] y0 = vdst[15:0];

    property p_vadd_wrap_lane0;
        @(posedge clk) disable iff (!rst_n)
        (start && (op == 5'd0)) |-> ##1 (y0 == a0 + b0);
    endproperty

    assert property (p_vadd_wrap_lane0)
        else `uvm_error("SIMD16", $sformatf("vadd lane0 mismatch: a0=%0h b0=%0h y0=%0h", a0, b0, y0));
endmodule
