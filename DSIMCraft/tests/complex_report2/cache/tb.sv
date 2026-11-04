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
    reg  [1:0] mstat = 2'b00;
    reg  [127:0] mrdata = 128'd0;
    wire mready;
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

    // ------- behavioral line memory (1024 lines, 16KB window) -------
    reg [127:0] mem [0:1023];
    reg [127:0] mem_exp [0:1023];   // reference image
    integer i, li;
    // memory command FSM: accept -> latency -> response
    reg [1:0] mst = 0;
    assign mready = (mst == 0);   // only accept when idle
    reg [31:0] maddr_l = 0;
    reg mw_l = 0;
    reg [127:0] mwdata_l = 0;
    integer lat;
    always @(posedge clk) begin
        if (mst == 0) begin
            if (mreq && mready) begin
                maddr_l  <= maddr;
                mw_l     <= mwe;
                mwdata_l <= mwdata;
                lat      <= 2;
                mst      <= 1;
            end
        end else if (mst == 1) begin
            lat <= lat - 1;
            if (lat == 1) begin
                if (mw_l) begin
                    if ($time > 46300000 && $time < 48000000)
                        $display("    [MEM2] mem[%0d] <= %h @%0t", maddr_l[13:4], mwdata_l, $time);
                    mem[maddr_l[13:4]] <= mwdata_l;
                    mstat <= 2'b10;      // write done
                    mst   <= 2;
                end else begin
                    mrdata <= mem[maddr_l[13:4]];
                    mstat  <= 2'b10;
                    mst    <= 2;
                end
            end
        end else begin
            mstat <= 2'b00;
            mst   <= 0;
        end
    end

    // ------- cpu-op monitors -------
    integer acc_n;    // accepted ops (req && ready)
    integer resp_n;   // rvalid pulses
    reg [31:0] resp_data;
    always @(posedge clk) begin
        if (rst_n && req && ready) acc_n = acc_n + 1;
        if (rst_n && rvalid) begin
            resp_n = resp_n + 1;
            resp_data = rdata;
        end
    end

    // flat reference (architectural memory image)
    reg [31:0] refm [0:4095];

    integer errors, exp_rdata_valid;
    reg [31:0] exp_rdata;

    task automatic cpu_op(input integer is_we, input [31:0] a, input [31:0] d);
        integer n0;
        begin
            @(posedge clk); #1;
            req = 1; we = (is_we != 0); addr = a; wdata = d;
            n0 = acc_n;
            while (acc_n == n0) begin @(posedge clk); #1; end
            req = 0;
            // wait response
            while (resp_n < acc_n) begin @(posedge clk); #1; end
        end
    endtask

    task automatic cpu_rd(input [31:0] a);
        begin
            exp_rdata = refm[a[13:2]];
            exp_rdata_valid = 1;
            cpu_op(0, a, 32'd0);
            if (resp_data !== exp_rdata) begin
                errors = errors + 1;
                $display("FAIL rd %h: got %h want %h", a, resp_data, exp_rdata);
            end
            exp_rdata_valid = 0;
        end
    endtask

    task automatic cpu_wr(input [31:0] a, input [31:0] d);
        begin
            cpu_op(1, a, d);
            refm[a[13:2]] = d;
        end
    endtask

        integer it;
    reg [13:0] rnd_a;
    reg [31:0] rnd_d;
    integer is_we;

    initial begin
        errors = 0; acc_n = 0; resp_n = 0;
        for (i = 0; i < 1024; i = i + 1) begin
            mem[i]     = {32'hC0DE0000 + i * 4 + 3, 32'hC0DE0000 + i * 4 + 2,
                          32'hC0DE0000 + i * 4 + 1, 32'hC0DE0000 + i * 4};
            mem_exp[i] = mem[i];
        end
        for (i = 0; i < 4096; i = i + 1)
            refm[i] = 32'hC0DE0000 + (i >> 2) * 4 + (i & 3);

        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        // t1: cold misses + hits (same line)
        cpu_rd(32'h0000_0100);
        cpu_rd(32'h0000_0104);   // same line -> hit
        cpu_wr(32'h0000_0108, 32'hAABB_CC08);
        cpu_rd(32'h0000_0108);   // hit, read back written
        $display("t1 done: hits=%0d misses=%0d", hits, misses);

        // t2: conflict eviction — same set, alternating tags forces victim churn
        for (it = 0; it < 24; it = it + 1) begin
            // set 3: addr = tag*256 + 0x30; two distant tags + one middle
            cpu_wr(32'h0001_0130 + (it << 12), 32'h1000_0000 + it);
        end
        // read them back: all but the last 2 per set were evicted; refm tracks truth
        for (it = 0; it < 24; it = it + 1)
            cpu_rd(32'h0001_0130 + (it << 12));
        $display("t2 done: hits=%0d misses=%0d", hits, misses);

        // t3: random phase — 400 mixed ops
        for (it = 0; it < 400; it = it + 1) begin
            rnd_a = $urandom;
            is_we = ($urandom_range(0, 9) < 3);
            rnd_d = $urandom;
            if (is_we) cpu_wr({18'd0, rnd_a}, rnd_d);
            else       cpu_rd({18'd0, rnd_a});
        end
        $display("t3 done: hits=%0d misses=%0d", hits, misses);

        // t4: flush dirty lines ONLY (no sweep help), compare memory vs reference
        @(posedge clk); #1; flush_req = 1;
        while (!flush_done) begin @(posedge clk); #1; end
        flush_req = 0;
        $display("t4 flushed (strict: no sweep assist)"); 
        for (i = 0; i < 1024; i = i + 1) begin
            mem_exp[i] = {refm[i*4+3], refm[i*4+2], refm[i*4+1], refm[i*4]};
            if (mem[i] !== mem_exp[i]) begin
                errors = errors + 1;
                if (errors < 6)
                    $display("FAIL mem[%0d]=%h want %h", i, mem[i], mem_exp[i]);
            end
        end
        if (errors == 0) $display("PASS t4: flush + memory compare");

        // t5: full read sweep vs reference (post-flush integrity)
        for (i = 0; i < 4096; i = i + 1)
            cpu_rd({18'd0, i[13:0]} * 32'd4);
        $display("t5 read sweep done: hits=%0d misses=%0d", hits, misses);

        errors = errors;   // placeholder
        for (i = 0; i < 1024; i = i + 1) begin
            // expected line content from ref
            mem_exp[i] = {refm[i*4+3], refm[i*4+2], refm[i*4+1], refm[i*4]};
            if (mem[i] !== mem_exp[i]) begin
                errors = errors + 1;
                if (errors < 6)
                    $display("FAIL mem[%0d]=%h want %h", i, mem[i], mem_exp[i]);
            end
        end
        if (hits == 0 || misses == 0) begin
            errors = errors + 1;
            $display("FAIL: stats degenerate hits=%0d misses=%0d", hits, misses);
        end
        $display("stats: hits=%0d misses=%0d", hits, misses);

        if (errors == 0) $display("CACHE_TEST: ALL PASS");
        else             $display("CACHE_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
