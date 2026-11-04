// cache perf bench: 400k random word ops (write-back cache with misses/evictions)
`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg  req = 0, we = 0, flush_req = 0;
    reg  [31:0] addr = 0, wdata = 0;
    wire ready, rvalid;
    wire [31:0] rdata;
    wire flush_done;
    wire mreq, mwe;
    wire [31:0] maddr;
    wire [127:0] mwdata;
    wire mready;
    reg [1:0] mstat;
    reg [127:0] mrdata;
    wire [15:0] hits, misses;

    cache2way dut (
        .clk(clk), .rst_n(rst_n),
        .req(req), .we(we), .addr(addr), .wdata(wdata),
        .ready(ready), .rvalid(rvalid), .rdata(rdata),
        .flush_req(flush_req), .flush_done(flush_done),
        .mreq(mreq), .mwe(mwe), .maddr(maddr), .mwdata(mwdata),
        .mready(mready), .mstat(mstat), .mrdata(mrdata),
        .hits(hits), .misses(misses)
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

    reg [127:0] mem [0:1023];
    reg [1:0] mst = 0;
    reg [31:0] maddr_l = 0;
    reg mw_l = 0;
    reg [127:0] mwdata_l = 0;
    integer lat;
    assign mready = (mst == 0);
    always @(posedge clk) begin
        if (mst == 0) begin
            if (mreq && mready) begin
                maddr_l <= maddr; mw_l <= mwe; mwdata_l <= mwdata;
                lat <= 2; mst <= 1;
            end
        end else if (mst == 1) begin
            lat <= lat - 1;
            if (lat == 1) begin
                if (mw_l) begin mem[maddr_l[13:4]] <= mwdata_l; mstat <= 2'b10; mst <= 2; end
                else begin mrdata <= mem[maddr_l[13:4]]; mstat <= 2'b10; mst <= 2; end
            end
        end else begin mstat <= 2'b00; mst <= 0; end
    end

    integer acc_n, resp_n;
    always @(posedge clk) begin
        if (rst_n && req && ready) acc_n = acc_n + 1;
        if (rst_n && rvalid) resp_n = resp_n + 1;
    end

    reg [31:0] refm [0:4095];
    reg [31:0] rnd_a, rnd_d, chk;
    integer i, n0, errors;

    task automatic cpu_op(input integer is_we, input [31:0] a, input [31:0] d);
        begin
            @(negedge clk);                 // drive mid-cycle: stable at following posedge
            req = 1; we = (is_we != 0); addr = a; wdata = d;
            n0 = acc_n;
            begin : accwait
                integer w;
                w = 0;
                while (acc_n == n0 && w < 100000) begin @(negedge clk); w = w + 1; end
                if (w >= 100000) begin
                    $display("STUCK i=%0d dut.st=%0d mst=%0d", i, dut.st, mst);
                    $finish;
                end
            end
            req = 0;                        // deassert mid-cycle after the accepting edge
            begin : rspwait
                integer w2;
                w2 = 0;
                while (resp_n < acc_n && w2 < 100000) begin @(negedge clk); w2 = w2 + 1; end
                if (w2 >= 100000) begin
                    $display("STUCK-RSP i=%0d dut.st=%0d resp=%0d acc=%0d", i, dut.st, resp_n, acc_n);
                    $finish;
                end
            end
        end
    endtask

    initial begin
        errors = 0; acc_n = 0; resp_n = 0; chk = 0;
        for (i = 0; i < 1024; i = i + 1)
            mem[i] = {32'hC0DE0000 + i*4+3, 32'hC0DE0000 + i*4+2,
                      32'hC0DE0000 + i*4+1, 32'hC0DE0000 + i*4};
        for (i = 0; i < 4096; i = i + 1)
            refm[i] = 32'hC0DE0000 + (i >> 2) * 4 + (i & 3);
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        for (i = 0; i < 1200000; i = i + 1) begin
            rng_state = xs32(rng_state); rnd_a = rng_state;
            rng_state = xs32(rng_state);
            if ((rng_state % 10) < 3) begin
                rng_state = xs32(rng_state); rnd_d = rng_state;
                cpu_op(1, {18'd0, rnd_a[13:0]}, rnd_d);
                refm[rnd_a[13:2]] = rnd_d;
            end else begin
                cpu_op(0, {18'd0, rnd_a[13:0]}, 32'd0);
                if (rdata !== refm[rnd_a[13:2]]) errors = errors + 1;
            end
        end
        // flush and fold memory into checksum
        @(negedge clk); flush_req = 1;
        while (!flush_done) @(negedge clk);
        flush_req = 0;
        for (i = 0; i < 4096; i = i + 1) chk = chk ^ refm[i] ^ (i * 4);
        if (errors == 0)
            $display("PERF cache: PASS ops=1200000 hits=%0d misses=%0d chk=0x%08x",
                     hits, misses, chk);
        else
            $display("PERF cache: FAIL errors=%0d", errors);
        $finish;
    end
endmodule
