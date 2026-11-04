`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg  [7:0] in = 0;
    wire [31:0] gen_out;
    wire [15:0] alt_out;
    wire [31:0] recur_out;
    wire [7:0]  cz_out, cx_out;
    wire [2:0]  ones_out;
    wire [15:0] meta_out;
    wire [7:0]  enum_probe, enum_last;

    svstress dut (
        .clk(clk), .rst_n(rst_n), .in(in),
        .gen_out(gen_out), .alt_out(alt_out), .recur_out(recur_out),
        .cz_out(cz_out), .cx_out(cx_out), .ones_out(ones_out),
        .meta_out(meta_out), .enum_probe(enum_probe), .enum_last(enum_last)
    );

    always #5 clk = ~clk;
    integer errors, i;
    reg [7:0] x;

    initial begin
        errors = 0;
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        // t1: generate-for lanes
        in = 8'h3C; @(posedge clk); #1;
        // lane g: y = in ^ (17*g + 10)
        if (gen_out !== {(8'h3C ^ 8'h3D), (8'h3C ^ 8'h2C),
                         (8'h3C ^ 8'h1B), (8'h3C ^ 8'h0A)}) begin
            errors = errors + 1; $display("FAIL t1 gen_out=%h", gen_out);
        end else $display("PASS t1: generate-for lanes");

        // t2: if-generate
        if (alt_out !== {8'h3C, 8'h3C}) begin
            errors = errors + 1; $display("FAIL t2 alt_out=%h", alt_out);
        end else $display("PASS t2: if-generate");

        // t3: recursion fib(12)=144
        if (recur_out !== 32'd144) begin
            errors = errors + 1; $display("FAIL t3 recur=%0d", recur_out);
        end else $display("PASS t3: iterative fib(12)=144");

        // t4: casez/casex sweep
        begin : t4blk
            reg [7:0] cz_exp, cx_exp;
            for (i = 0; i < 256; i = i + 1) begin
                x = i[7:0];
                in = x; @(posedge clk); #1;
                // ref casez (item order matters, top-down)
                if      (x[7])               cz_exp = 8'd1;   // 8'b1???????
                else if (x[7:6] == 2'b01)    cz_exp = 8'd2;   // 8'b01??????
                else if ((x & 8'h1F) == 8'h01) cz_exp = 8'd3; // 8'b???00001
                else if ((x & 8'hF0) == 8'h00) cz_exp = 8'd4; // 8'h0?
                else                         cz_exp = 8'd5;
                // ref casex (inputs never x here)
                if      ((x & 8'h3F) == 8'h01) cx_exp = 8'hA1;              // xx000001
                else if ((x & 8'hF0) == 8'h00 && (x & 8'h03) == 8'h02)
                                              cx_exp = 8'hA2;              // 0000xx10
                else if ((x & 8'hF0) == 8'h10) cx_exp = 8'hA3;              // 0001????
                else                          cx_exp = 8'hA4;
                if (cz_out !== cz_exp) begin
                    errors = errors + 1; $display("FAIL t4 casez x=%h got=%0d want=%0d", x, cz_out, cz_exp);
                end
                if (cx_out !== cx_exp) begin
                    errors = errors + 1; $display("FAIL t4 casex x=%h got=%h want=%h", x, cx_out, cx_exp);
                end
            end
            if (errors == 0) $display("PASS t4: casez/casex 256-sweep");
        end

        // t5: $countones (registered: check against previous input)
        in = 8'h5B; @(posedge clk); #1; @(posedge clk); #1;
        if (ones_out !== 3'd5) begin
            errors = errors + 1; $display("FAIL t5 ones=%0d want 5", ones_out);
        end else $display("PASS t5: $countones=5");

        // t6: $bits/$clog2 -> 8*256+6
        if (meta_out !== 16'd2054) begin
            errors = errors + 1; $display("FAIL t6 meta=%0d want 2054", meta_out);
        end else $display("PASS t6: $bits/$clog2 math");

        // t7: enum
        if (enum_probe !== 8'd1 || enum_last !== 8'd2) begin
            errors = errors + 1; $display("FAIL t7 enum %0d %0d", enum_probe, enum_last);
        end else $display("PASS t7: enum values");

        if (errors == 0) $display("SVSTRESS_TEST: ALL PASS");
        else             $display("SVSTRESS_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
