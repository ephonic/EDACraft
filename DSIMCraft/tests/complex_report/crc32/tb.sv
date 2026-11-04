`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg  soc = 0, eoc = 0, valid = 0;
    reg  [7:0] data_in = 0;
    wire crc_valid;
    wire [31:0] crc_out;
    wire busy;

    crc32_engine dut (
        .clk(clk), .rst_n(rst_n), .soc(soc), .eoc(eoc), .valid(valid),
        .data_in(data_in), .crc_valid(crc_valid), .crc_out(crc_out), .busy(busy)
    );

    always #5 clk = ~clk;

    integer errors, f, b, i, guard;

    // reference: non-reflected poly 0x04C11DB7 with bit-reversal (independent of DUT formulation)
    function automatic [31:0] rev32(input [31:0] x);
        reg [31:0] r;
        integer k;
        begin
            for (k = 0; k < 32; k = k + 1) r[31-k] = x[k];
            rev32 = r;
        end
    endfunction
    function automatic [7:0] rev8(input [7:0] x);
        reg [7:0] r;
        integer k;
        begin
            for (k = 0; k < 8; k = k + 1) r[7-k] = x[k];
            rev8 = r;
        end
    endfunction
    function automatic [31:0] crc32_ref(input [7:0] frame [0:63], input integer len);
        integer j, k;
        reg [31:0] c;
        begin
            c = 32'hFFFFFFFF;
            for (j = 0; j < len; j = j + 1) begin
                c = c ^ ({24'd0, rev8(frame[j])} << 24);
                for (k = 0; k < 8; k = k + 1)
                    c = c[31] ? ((c << 1) ^ 32'h04C11DB7) : (c << 1);
            end
            crc32_ref = rev32(c ^ 32'hFFFFFFFF);
        end
    endfunction

    // frame memory
    reg [7:0] frame [0:63];
    integer   flen;
    reg [31:0] exp_crc;

    task automatic run_frame(input integer len, input integer gap);
        begin
            // wait idle
            guard = 0;
            while (busy && guard < 100) begin @(posedge clk); #1; guard = guard + 1; end
            for (b = 0; b < len; b = b + 1) begin
                @(posedge clk); #1;
                valid = ($urandom_range(0, 3) > 0) || (b == len - 1) || (b % (gap+1) == 0);
                if (b == len - 1) valid = 1'b1;   // always send final byte promptly
                soc = (b == 0);
                eoc = (b == len - 1);
                data_in = frame[b];
                if (!valid) begin
                    // retry this byte
                     b = b - 1;
                end else begin
                    // hold random extra idle gap sometimes
                    if ($urandom_range(0, 4) == 0 && b < len - 1) begin
                        @(posedge clk); #1; valid = 0; soc = 0; eoc = 0;
                    end
                end
            end
            @(posedge clk); #1; valid = 0; soc = 0; eoc = 0;
            // wait crc_valid
            guard = 0;
            while (!crc_valid && guard < 20) begin @(posedge clk); #1; guard = guard + 1; end
            if (!crc_valid) begin
                errors = errors + 1;
                $display("FAIL frame(len=%0d): no crc_valid", len);
            end else if (crc_out !== exp_crc) begin
                errors = errors + 1;
                $display("FAIL frame(len=%0d): got %h want %h", len, crc_out, exp_crc);
            end
        end
    endtask

    initial begin
        errors = 0;
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        // KAT: "123456789" -> 0xCBF43926
        flen = 9;
        for (i = 0; i < flen; i = i + 1) frame[i] = 8'h31 + i[7:0];
        exp_crc = 32'hCBF43926;
        run_frame(flen, 1);
        if (errors == 0) $display("PASS KAT 123456789 -> CBF43926");

        // single byte frame
        frame[0] = 8'h00; exp_crc = crc32_ref(frame, 1);
        run_frame(1, 0);
        if (errors == 0) $display("PASS single-byte frame");

        // 20 random frames
        for (f = 0; f < 20; f = f + 1) begin
            flen = $urandom_range(1, 64);
            for (i = 0; i < flen; i = i + 1) frame[i] = $urandom;
            exp_crc = crc32_ref(frame, flen);
            run_frame(flen, $urandom_range(0, 3));
        end
        $display("random frames done");

        if (errors == 0) $display("CRC32_TEST: ALL PASS");
        else             $display("CRC32_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
