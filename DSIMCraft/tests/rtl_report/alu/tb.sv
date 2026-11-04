`timescale 1ns/1ps
module tb;
    reg  [3:0]  op;
    reg  [15:0] a, b;
    reg          cin;
    wire [15:0] result;
    wire zero, neg, ovf;

    alu #(.W(16)) dut(.op(op), .a(a), .b(b), .cin(cin),
                      .result(result), .zero(zero), .neg(neg), .ovf(ovf));

    integer errors, tests;
    reg [15:0] exp;

    // golden model (uses same operators but computed at tb level for cross-check)
    function [15:0] gold(input [3:0] gop, input [15:0] ga, input [15:0] gb, input gcin);
        reg [31:0] m; reg [3:0] sh;
        begin
            m = 0; sh = gb[3:0];
            case (gop)
                4'd0:  gold = ga + gb + gcin;
                4'd1:  gold = ga - gb - gcin;
                4'd2:  gold = ga & gb;
                4'd3:  gold = ga | gb;
                4'd4:  gold = ga ^ gb;
                4'd5:  gold = ga << sh;
                4'd6:  gold = ga >> sh;
                4'd7:  gold = $signed(ga) >>> sh;
                4'd8:  gold = ($signed(ga) < $signed(gb)) ? 16'd1 : 16'd0;
                4'd9:  gold = (ga < gb) ? 16'd1 : 16'd0;
                4'd10: begin m = $signed(ga) * $signed(gb); gold = m[15:0]; end
                4'd11: gold = (gb == 0) ? 16'hFFFF : $signed(ga) / $signed(gb);
                4'd12: gold = (gb == 0) ? ga : $signed(ga) % $signed(gb);
                4'd13: begin
                    gold = 16;
                    for (integer k = 15; k >= 0; k = k - 1)
                        if (ga[k] && gold == 16) gold = 15 - k;
                    if (ga == 16'hFFFF) gold = 0;
                end
                4'd14: gold = ($signed(ga) < $signed(gb)) ? ga : gb;
                4'd15: gold = (ga << sh) | (ga >> (16 - sh));
            endcase
        end
    endfunction

    // stimulus: LFSR random
    reg [31:0] lfsr;
    integer i, j;

    initial begin
        errors = 0; tests = 0;
        lfsr = 32'hDEADBEEF;

        // directed corner cases
        a = 16'h0000; b = 16'h0000; cin = 0; op = 0; #10;
        if (result !== 16'h0000 || zero !== 1'b1) begin errors++; $display("FAIL corner zero: r=%h z=%b", result, zero); end
        tests++;

        a = 16'h7FFF; b = 16'h0001; cin = 0; op = 0; #10;
        if (ovf !== 1'b1) begin errors++; $display("FAIL signed overflow: r=%h ovf=%b", result, ovf); end
        tests++;

        a = 16'h8000; b = 16'h0001; cin = 0; op = 4'd1; #10;
        if (ovf !== 1'b1) begin errors++; $display("FAIL sub overflow: r=%h ovf=%b", result, ovf); end
        tests++;

        a = 16'h8000; b = 16'h0001; op = 4'd7; #10;  // SRA of negative
        if (result !== 16'hC000) begin errors++; $display("FAIL sra: r=%h", result); end
        tests++;

        a = 16'h0003; b = 16'h0000; op = 4'd11; #10; // div by zero
        if (result !== 16'hFFFF) begin errors++; $display("FAIL div0: r=%h", result); end
        tests++;

        // random sweep across all ops
        for (j = 0; j < 16; j = j + 1) begin
            op = j[3:0];
            for (i = 0; i < 64; i = i + 1) begin
                lfsr = (lfsr << 1) | (^lfsr[31:29] ^ lfsr[31] ^ lfsr[28]);
                a = lfsr[15:0];
                lfsr = (lfsr << 1) | (^lfsr[31:29] ^ lfsr[31] ^ lfsr[28]);
                b = lfsr[15:0];
                cin = lfsr[0];
                #10;
                exp = gold(op, a, b, cin);
                tests++;
                if (result !== exp) begin
                    errors++;
                    $display("FAIL op=%0d a=%h b=%h cin=%b: got=%h exp=%h", op, a, b, cin, result, exp);
                end
            end
        end

        $display("ALU_TEST: %0d tests, %0d errors", tests, errors);
        if (errors == 0) $display("ALU_TEST: ALL PASS");
        $finish;
    end
endmodule
