`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;

    reg         m_start = 0;
    reg signed [15:0] m_a = 0, m_b = 0;
    wire        m_busy, m_done;
    wire signed [31:0] m_prod;

    reg  [31:0] d_dvd = 0;
    reg  [15:0] d_dvs = 0;
    reg         d_start = 0;
    wire        d_busy, d_done;
    wire [31:0] d_quo;
    wire [15:0] d_rem;

    booth_mul16 u_mul (
        .clk(clk), .rst_n(rst_n), .start(m_start), .a(m_a), .b(m_b),
        .busy(m_busy), .done(m_done), .product(m_prod)
    );
    udiv32_16 u_div (
        .clk(clk), .rst_n(rst_n), .start(d_start), .dvd(d_dvd), .dvs(d_dvs),
        .busy(d_busy), .done(d_done), .quo(d_quo), .rem_o(d_rem)
    );

    always #5 clk = ~clk;

    integer errors;
    integer i, guard;
    reg signed [15:0] ra, rb;
    reg signed [31:0] exp_p;
    reg [31:0] rdvd, exp_q;
    reg [15:0] rdvs, exp_r;

    task automatic mul1(input signed [15:0] ta, input signed [15:0] tb);
        begin
            @(posedge clk); #1;
            m_a = ta; m_b = tb; m_start = 1;
            @(posedge clk); #1; m_start = 0;
            guard = 0;
            while (!m_done && guard < 50) begin @(posedge clk); #1; guard = guard + 1; end
            if (!m_done) begin
                errors = errors + 1;
                $display("FAIL mul(%0d,%0d): timeout", ta, tb);
            end else begin
                exp_p = ta * tb;
                if (m_prod !== exp_p) begin
                    errors = errors + 1;
                    $display("FAIL mul(%0d,%0d): got %0d want %0d", ta, tb, m_prod, exp_p);
                end
            end
        end
    endtask

    task automatic div1(input [31:0] tdvd, input [15:0] tdvs);
        begin
            @(posedge clk); #1;
            d_dvd = tdvd; d_dvs = tdvs; d_start = 1;
            @(posedge clk); #1; d_start = 0;
            guard = 0;
            while (!d_done && guard < 100) begin @(posedge clk); #1; guard = guard + 1; end
            if (!d_done) begin
                errors = errors + 1;
                $display("FAIL div(%0d,%0d): timeout", tdvd, tdvs);
            end else begin
                if (tdvs == 0) begin
                    exp_q = 32'hFFFFFFFF; exp_r = tdvd[15:0];
                end else begin
                    exp_q = tdvd / {16'd0, tdvs}; exp_r = tdvd % {16'd0, tdvs};
                end
                if (d_quo !== exp_q || d_rem !== exp_r) begin
                    errors = errors + 1;
                    $display("FAIL div(%0d,%0d): q=%0d want %0d r=%0d want %0d",
                             tdvd, tdvs, d_quo, exp_q, d_rem, exp_r);
                end
            end
        end
    endtask

    initial begin
        errors = 0;
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        // multiplier corners
        mul1(16'sd0,        16'sd0);
        mul1(16'sd1,        16'sd1);
        mul1(-16'sd1,      -16'sd1);
        mul1(16'sh8000,     16'sh8000);   // -32768 * -32768 = 2^30
        mul1(16'sh8000,     16'sd1);
        mul1(16'sd1,        16'sh8000);
        mul1(-16'sd1,       16'sh7FFF);
        mul1(16'sh7FFF,     16'sh7FFF);
        mul1(16'sh7FFF,    -16'sh8000);
        mul1(-16'sd21845,   16'sd21845);
        mul1(16'sd12345,   -16'sd6789);
        $display("mul corners done");

        // divider corners
        div1(32'd0,         16'd0);
        div1(32'd0,         16'd5);
        div1(32'd12345,     16'd0);
        div1(32'hFFFFFFFF,  16'd0);
        div1(32'd7,         16'd1);
        div1(32'hFFFFFFFF,  16'hFFFF);
        div1(32'hFFFFFFFF,  16'd1);
        div1(32'h00010000,  16'd1);
        div1(32'h0000FFFF,  16'h0000FFFF);
        div1(32'd1,         16'h0001);
        div1(32'h80000000,  16'h0002);
        $display("div corners done");

        // randoms: 120 mul + 120 div interleaved (fixed seed for repro)
        for (i = 0; i < 120; i = i + 1) begin
            ra = $urandom;
            rb = $urandom;
            mul1(ra, rb);
            rdvd = $urandom;
            rdvs = $urandom_range(1, 65535);
            div1(rdvd, rdvs);
        end
        $display("randoms done");

        if (errors == 0) $display("MULDIV_TEST: ALL PASS");
        else             $display("MULDIV_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
