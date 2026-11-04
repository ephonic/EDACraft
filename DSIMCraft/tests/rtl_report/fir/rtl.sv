// 4-tap transposed FIR, 3-stage pipeline: MAC + saturating output
`timescale 1ns/1ps
module fir4 #(
    parameter W = 12,
    parameter COEF_W = 10,
    parameter N = 4
)(
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 in_valid,
    input  wire signed [W-1:0]  in_data,
    output reg  signed [W+8:0]  out_data,
    output reg                  out_valid
);
    localparam signed [COEF_W-1:0] C0 = 10'sd27;
    localparam signed [COEF_W-1:0] C1 = 10'sd140;
    localparam signed [COEF_W-1:0] C2 = 10'sd217;
    localparam signed [COEF_W-1:0] C3 = 10'sd140;

    // delay line
    reg signed [W-1:0] z [0:N-1];

    // stage 1 regs: products
    reg signed [W+COEF_W-1:0] p0, p1, p2, p3;
    reg                        v1;
    // stage 2 regs: partial sums
    reg signed [W+COEF_W:0]   s01, s23;
    reg                        v2;

    integer k;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < N; k = k + 1) z[k] <= 0;
            p0 <= 0; p1 <= 0; p2 <= 0; p3 <= 0; v1 <= 0;
            s01 <= 0; s23 <= 0; v2 <= 0;
            out_data <= 0; out_valid <= 0;
        end else begin
            // stage 1: shift delay line + multiply
            if (in_valid) begin
                z[0] <= in_data;
                for (k = 1; k < N; k = k + 1) z[k] <= z[k-1];
            end
            p0 <= z[0] * C0;
            p1 <= z[1] * C1;
            p2 <= z[2] * C2;
            p3 <= z[3] * C3;
            v1 <= in_valid;

            // stage 2: partial sums
            s01 <= p0 + p1;
            s23 <= p2 + p3;
            v2  <= v1;

            // stage 3: final add + output
            out_data  <= s01 + s23;
            out_valid <= v2;
        end
    end
endmodule
