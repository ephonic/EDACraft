`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0, in_valid = 0;
    reg signed [11:0] in_data = 0;
    wire signed [20:0] out_data;
    wire out_valid;

    fir4 #(.W(12), .COEF_W(10), .N(4)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_data(in_data),
        .out_data(out_data), .out_valid(out_valid)
    );

    always #5 clk = ~clk;

    localparam C0 = 27, C1 = 140, C2 = 217, C3 = 140;

    integer errors, i, latency, sent_cnt, recv_cnt;
    integer golden_q [0:255];  // reference outputs in order
    integer exp;
    reg [31:0] lfsr;

    // reference model
    integer z0, z1, z2, z3;

    initial begin
        errors = 0; sent_cnt = 0; recv_cnt = 0;
        lfsr = 32'h1234ABCD;
        z0 = 0; z1 = 0; z2 = 0; z3 = 0;
        @(posedge clk); #1; rst_n = 1; #1;

        // impulse response test: single impulse => coefficients appear at output
        golden_q[0] = 0; // impulse's own output: delay line was all-zero at multiply time
        in_valid = 1; in_data = 12'sd1000; @(posedge clk); #1;
        in_valid = 0; in_data = 0;
        sent_cnt = 1;

        // drain 5 outputs
        for (i = 0; i < 5; i = i + 1) begin
            @(posedge clk); #1;
        end
        $display("FIR impulse done (outputs consumed below in random phase)");

        // reset reference model
        z0 = 1000; z1 = 0; z2 = 0; z3 = 0;  // impulse already shifted in
        // note: dut delay line currently holds [1000,0,0,0]

        // random walk input, backpressure with gaps
        for (i = 0; i < 200; i = i + 1) begin
            if ((i % 7) == 3) begin
                // gap cycle: no valid input
                in_valid = 0;
                @(posedge clk); #1;
            end
            in_data = (lfsr[10:0] % 100) - 50; // -50..49 (LFSR: $random unsupported in dsim)
            lfsr = (lfsr << 1) | (^lfsr[31:29] ^ lfsr[31] ^ lfsr[28]);
            in_valid = 1;
            // golden advance: output = z0*C0+z1*C1+z2*C2+z3*C3 (matches 3-cycle pipe)
            golden_q[sent_cnt] = z0*C0 + z1*C1 + z2*C2 + z3*C3;
            z3 = z2; z2 = z1; z1 = z0; z0 = in_data;
            sent_cnt = sent_cnt + 1;
            @(posedge clk); #1;
        end
        in_valid = 0;

        // collect remaining outputs
        for (i = 0; i < 10; i = i + 1) begin
            @(posedge clk); #1;
        end

        if (errors == 0) $display("FIR_TEST: PASS (%0d samples driven)", sent_cnt);
        else $display("FIR_TEST: %0d ERRORS", errors);
        $finish;
    end

    // output monitor
    integer expect_idx;
    initial expect_idx = 0;
    always @(posedge clk) begin
        if (!rst_n) expect_idx = 0;
        else if (out_valid) begin
            if (expect_idx < 256) begin
                exp = golden_q[expect_idx];
                if (out_data !== exp[20:0]) begin
                    errors = errors + 1;
                    $display("FAIL fir out[%0d]: got=%0d exp=%0d", expect_idx, out_data, exp);
                end
            end
            expect_idx = expect_idx + 1;
        end
    end
endmodule
