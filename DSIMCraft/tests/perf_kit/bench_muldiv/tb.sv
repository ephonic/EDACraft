// muldiv perf bench: 30k random signed mul + unsigned div vectors
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

    // deterministic xorshift32 (pure function; caller advances state)
    reg [31:0] rng_state = 32'h1A2B3C4D;
    function automatic [31:0] xs32(input [31:0] s);
        reg [31:0] t;
        begin
            t = s ^ (s << 13);
            t = t ^ (t >> 17);
            t = t ^ (t << 5);
            xs32 = t;
        end
    endfunction

    integer errors, i, guard;
    reg signed [15:0] ra, rb;
    reg [31:0] rdvd;
    reg [15:0] rdvs;
    reg [31:0] chk;
    reg signed [31:0] exp_p;
    reg [31:0] exp_q, exp_r;

    task automatic mul1(input signed [15:0] ta, input signed [15:0] tb);
        begin
            @(negedge clk);
            m_a = ta; m_b = tb; m_start = 1;
            @(negedge clk); m_start = 0;
            guard = 0;
            while (!m_done && guard < 2000) begin @(negedge clk); guard = guard + 1; end
            exp_p = ta * tb;
            if (m_prod !== exp_p) errors = errors + 1;
            chk = chk ^ m_prod;
        end
    endtask

    task automatic div1(input [31:0] tdvd, input [15:0] tdvs);
        begin
            @(negedge clk);
            d_dvd = tdvd; d_dvs = tdvs; d_start = 1;
            @(negedge clk); d_start = 0;
            guard = 0;
            while (!d_done && guard < 2000) begin @(negedge clk); guard = guard + 1; end
            if (tdvs == 0) begin exp_q = 32'hFFFFFFFF; exp_r = tdvd[15:0]; end
            else begin exp_q = tdvd / {16'd0, tdvs}; exp_r = tdvd % {16'd0, tdvs}; end
            if (d_quo !== exp_q || d_rem !== exp_r) errors = errors + 1;
            chk = chk ^ d_quo ^ {16'd0, d_rem};
        end
    endtask

    initial begin
        errors = 0; chk = 0;
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;
        for (i = 0; i < 600000; i = i + 1) begin
            rng_state = xs32(rng_state); ra = rng_state[15:0];
            rng_state = xs32(rng_state); rb = rng_state[15:0];
            mul1(ra, rb);
            rng_state = xs32(rng_state); rdvd = rng_state;
            rng_state = xs32(rng_state); rdvs = rng_state[15:0];
            div1(rdvd, rdvs);
        end
        if (errors == 0) $display("PERF muldiv: PASS vectors=1200000 chk=0x%08x", chk);
        else             $display("PERF muldiv: FAIL errors=%0d", errors);
        $finish;
    end
endmodule
