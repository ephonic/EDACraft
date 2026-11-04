`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg  [3:0]  c_valid = 0;
    reg  [31:0] c_data = 0;
    wire [3:0]  c_ready;
    wire        mem_wr;
    wire [7:0]  mem_addr, mem_wdata;
    wire [1:0]  mem_sel;
    wire [1:0]  last_served;
    wire [3:0]  occ_nz;

    rr_mux_sram dut (
        .clk(clk), .rst_n(rst_n),
        .c_valid(c_valid), .c_data(c_data), .c_ready(c_ready),
        .mem_wr(mem_wr), .mem_addr(mem_addr), .mem_wdata(mem_wdata),
        .mem_sel(mem_sel), .last_served(last_served), .occ_nz(occ_nz)
    );

    always #5 clk = ~clk;

    localparam PER_CLIENT = 64;

    integer errors;
    integer i, done_push;
    // per-client scoreboard
    integer rx_cnt [0:3];
    integer seq_err [0:3];
    reg [7:0] tag_exp [0:3];
    // rotation check
    reg [3:0] occ_prev;
    reg [1:0] last_prev;
    integer rot_err;
    // push-side sequence tracking
    integer tx_cnt [0:3];

    initial begin
        errors = 0; rot_err = 0; done_push = 0;
        occ_prev = 4'h0; last_prev = 2'd3;
        for (i = 0; i < 4; i = i + 1) begin
            rx_cnt[i] = 0; seq_err[i] = 0; tx_cnt[i] = 0;
            tag_exp[i] = {i[1:0], 6'd0};
        end
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        // push phase: random valid per client; data = {client[7:6], seq[5:0]}
        while (!done_push) begin
            @(posedge clk); #1;
            done_push = 1;
            for (i = 0; i < 4; i = i + 1) begin
                if (tx_cnt[i] < PER_CLIENT) begin
                    done_push = 0;
                    c_valid[i] = ($urandom_range(0, 9) > 3);        // 70% duty
                    if (tx_cnt[i] >= PER_CLIENT - 1) c_valid[i] = 1'b1; // finish tail
                    c_data[8*i +: 8] = {i[1:0], tx_cnt[i][5:0]};
                    if (c_valid[i] && c_ready[i])
                        tx_cnt[i] = tx_cnt[i] + 1;                  // accepted at next edge
                end else begin
                    c_valid[i] = 1'b0;
                end
            end
        end
        c_valid = 4'h0;
        $display("push phase done");

        // drain phase (up to 4*PER_CLIENT + slack cycles)
        i = 0;
        while (i < 4*PER_CLIENT + 16 && !(occ_nz == 4'h0 && mem_wr == 1'b0)) begin
            @(posedge clk); #1;
            i = i + 1;
        end
        if (occ_nz != 4'h0) begin
            errors = errors + 1;
            $display("FAIL: FIFOs not drained, occ_nz=%b", occ_nz);
        end

        // checks
        for (i = 0; i < 4; i = i + 1) begin
            if (rx_cnt[i] !== PER_CLIENT) begin
                errors = errors + 1;
                $display("FAIL: client%0d received %0d (want %0d)", i, rx_cnt[i], PER_CLIENT);
            end
            if (seq_err[i] !== 0) begin
                errors = errors + 1;
                $display("FAIL: client%0d seq errors: %0d", i, seq_err[i]);
            end
        end
        if (rot_err != 0) begin
            errors = errors + 1;
            $display("FAIL: rotation violations: %0d", rot_err);
        end else $display("PASS: strict round-robin rotation held");
        if (errors == 0) $display("ARB_TEST: ALL PASS");
        else             $display("ARB_TEST: %0d ERRORS", errors);
        $finish;
    end

    // snoop drain stream every cycle
    initial begin
        forever begin
            @(posedge clk); #1;
            if (mem_wr === 1'b1) begin
                if (mem_wdata[7:6] !== mem_sel[1:0]) begin
                    seq_err[mem_sel] = seq_err[mem_sel] + 1;
                    $display("FAIL @%0t: tag mismatch sel=%0d data=%h", $time, mem_sel, mem_wdata);
                end else if (mem_wdata !== tag_exp[mem_sel]) begin
                    seq_err[mem_sel] = seq_err[mem_sel] + 1;
                    $display("FAIL @%0t: client%0d seq got %0d want %0d",
                             $time, mem_sel, mem_wdata[5:0], tag_exp[mem_sel][5:0]);
                end else begin
                    tag_exp[mem_sel] = tag_exp[mem_sel] + 8'd1;
                end
                rx_cnt[mem_sel] = rx_cnt[mem_sel] + 1;
                // rotation rule: if all clients were non-empty post-prev-edge,
                // this beat must come from last_prev+1
                if (occ_prev == 4'hF && mem_sel !== ((last_prev + 2'd1) & 2'b11)) begin
                    rot_err = rot_err + 1;
                    $display("FAIL @%0t: rotation break last=%0d got sel=%0d",
                             $time, last_prev, mem_sel);
                end
            end
            occ_prev  = occ_nz;
            last_prev = last_served;
        end
    end
endmodule
