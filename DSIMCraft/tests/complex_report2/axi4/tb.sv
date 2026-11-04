`timescale 1ns/1ps
module tb;
    localparam ID_W = 4;
    reg clk = 0, rst_n = 0;

    reg  [31:0] awaddr = 0; reg [3:0] awlen = 0; reg [1:0] awburst = 0;
    reg  [ID_W-1:0] awid = 0; reg awvalid = 0; wire awready;
    reg  [31:0] wdata = 0; reg [3:0] wstrb = 0; reg wlast = 0; reg wvalid = 0; wire wready;
    wire bvalid; reg bready = 0; wire [1:0] bresp; wire [ID_W-1:0] bid;
    reg  [31:0] araddr = 0; reg [3:0] arlen = 0; reg [1:0] arburst = 0;
    reg  [ID_W-1:0] arid = 0; reg arvalid = 0; wire arready;
    wire rvalid; reg rready = 0; wire [31:0] rdata; wire [1:0] rresp;
    wire [ID_W-1:0] rid; wire rlast;

    axi4_slave #(.ID_W(ID_W)) dut (
        .clk(clk), .rst_n(rst_n),
        .awaddr(awaddr), .awlen(awlen), .awburst(awburst), .awid(awid),
        .awvalid(awvalid), .awready(awready),
        .wdata(wdata), .wstrb(wstrb), .wlast(wlast), .wvalid(wvalid), .wready(wready),
        .bvalid(bvalid), .bready(bready), .bresp(bresp), .bid(bid),
        .araddr(araddr), .arlen(arlen), .arburst(arburst), .arid(arid),
        .arvalid(arvalid), .arready(arready),
        .rvalid(rvalid), .rready(rready), .rdata(rdata), .rresp(rresp),
        .rid(rid), .rlast(rlast)
    );

    always #5 clk = ~clk;

    integer errors, i, j, guard;
    // reference memory (same init pattern)
    reg [31:0] model [0:255];
    function automatic [31:0] pat(input [7:0] a);
        pat = {a, ~a, (a ^ 8'h5A), (a + 8'hA5)};
    endfunction
    function automatic [7:0] nxt(input [7:0] a, input [1:0] burst, input [3:0] len);
        reg [7:0] mask, base;
        begin
            if (burst == 2'b10) begin
                mask = {4'd0, len};         // (len+1)-word window -> mask = len
                base = a & ~mask;
                nxt  = base | (((a & mask) + 8'd1) & mask);
            end else nxt = a + 8'd1;
        end
    endfunction
    function automatic [31:0] merge(input [31:0] d, input [31:0] o, input [3:0] s);
        merge = {s[3] ? d[31:24] : o[31:24], s[2] ? d[23:16] : o[23:16],
                 s[1] ? d[15:8]  : o[15:8],  s[0] ? d[7:0]   : o[7:0]};
    endfunction

    // race-free AR monitor
    integer armon_n;
    always @(posedge clk) begin
        if (rst_n && arvalid && arready) armon_n = armon_n + 1;
    end

    task automatic ar_issue(input [31:0] addr, input [3:0] len, input [1:0] burst,
                            input [ID_W-1:0] id);
        integer n0;
        begin
            @(posedge clk); #1;
            araddr = addr; arlen = len; arburst = burst; arid = id; arvalid = 1;
            n0 = armon_n;
            while (armon_n == n0) begin @(posedge clk); #1; end
            arvalid = 0;
        end
    endtask

    task automatic rand_delay;
        integer d, k;
        begin
            d = $urandom_range(0, 3);
            for (k = 0; k < d; k = k + 1) @(posedge clk);
        end
    endtask

    // race-free W/B-channel monitors
    integer wmon_n, bmon_n;
    reg [1:0] bmon_resp;
    reg [3:0] bmon_id;
    always @(posedge clk) begin
        if (rst_n && wvalid && wready) wmon_n = wmon_n + 1;
        if (rst_n && bvalid && bready) begin
            bmon_resp = bresp; bmon_id = bid; bmon_n = bmon_n + 1;
        end
    end

    // write burst: legal wlast at beat len (or early_last); returns bresp
    task automatic wr_burst(input [31:0] addr, input [3:0] len, input [1:0] burst,
                            input [ID_W-1:0] id, input [3:0] strb,
                            input integer early_last,
                            output [1:0] resp);
        reg [7:0] wa, na;
        reg [3:0] beat;
        integer n0, guard;
        begin
            @(posedge clk); #1;
            wmon_n = 0; bmon_n = 0;
            awaddr = addr; awlen = len; awburst = burst; awid = id; awvalid = 1;
            wvalid = 1; wstrb = strb; bready = 0;
            wa = addr[9:2]; beat = 0;
            guard = 0;
            while (beat <= len && guard < 60) begin
                guard = guard + 1;
                wdata = {wa, ~wa, (wa ^ 8'h3C), (wa + {4'd0, beat})};
                wlast = (beat == len) || (early_last >= 0 && beat == early_last);
                if (burst != 2'b00)
                    model[wa] = merge(wdata, model[wa], strb);
                na  = nxt(wa, burst, len);
                n0  = wmon_n;
                while (wmon_n == n0 && guard < 60) begin
                    guard = guard + 1;
                    @(posedge clk); #1;
                end
                #1;                       // just after the handshake edge
                if (wlast) begin
                    wvalid = 0; wlast = 0; awvalid = 0;
                    beat = len + 1;
                end else begin
                    wa = na; beat = beat + 1;
                end
            end
            // B response
            n0 = bmon_n;
            while (bmon_n == n0 && guard < 120) begin
                guard = guard + 1;
                @(posedge clk); #1;
                if (bmon_n == n0) bready = 1;   // apply backpressure a bit late on purpose
            end
            bready = 0;
            #1;
            resp = bmon_resp;
            if (bmon_id !== id) begin
                errors = errors + 1;
                $display("FAIL wr: bid=%0d want %0d", bmon_id, id);
            end
        end
    endtask

    // race-free R-channel monitor: samples pre-edge values at handshake
    integer rmon_n;
    reg [31:0] rmon_data [0:15];
    reg [3:0]  rmon_id   [0:15];
    reg        rmon_last [0:15];
    reg [1:0]  rmon_resp [0:15];
    always @(posedge clk) begin
        if (rst_n && rvalid && rready) begin
            rmon_data[rmon_n] = rdata;
            rmon_id[rmon_n]   = rid;
            rmon_last[rmon_n] = rlast;
            rmon_resp[rmon_n] = rresp;
            rmon_n = rmon_n + 1;
        end
    end

    // read burst: verify against model via monitor captures
    task automatic rd_burst(input [31:0] addr, input [3:0] len, input [1:0] burst,
                            input [ID_W-1:0] id, output [1:0] resp);
        reg [7:0] wa;
        reg [31:0] wexp;
        integer bad, b, guard;
        begin
            rmon_n = 0;
            ar_issue(addr, len, burst, id);
            rand_delay();
            rready = 1;
            guard = 0;
            while (rmon_n < ((burst == 2'b00) ? 1 : len + 1) && guard < 60) begin
                @(posedge clk); #1; guard = guard + 1;
            end
            rready = 0;   // drop immediately: no trailing edge that could re-handshake the last beat
            if (rmon_n != ((burst == 2'b00) ? 1 : len + 1)) begin
                errors = errors + 1;
                $display("FAIL rd: got %0d beats want %0d (addr=%h burst=%b)",
                         rmon_n, (burst == 2'b00) ? 1 : len + 1, addr, burst);
            end else begin
                wa = addr[9:2]; bad = 0;
                for (b = 0; b < ((burst == 2'b00) ? 1 : len + 1); b = b + 1) begin
                    if (burst == 2'b00) wexp = 32'd0;
                    else                wexp = model[wa];
                    if (rmon_data[b] !== wexp) begin
                        bad = bad + 1;
                        $display("FAIL rd beat%0d: got %h want %h (addr=%h burst=%b)",
                                 b, rmon_data[b], wexp, addr, burst);
                    end
                    if (rmon_id[b] !== id) begin
                        errors = errors + 1;
                        $display("FAIL rd beat%0d rid=%0d want %0d", b, rmon_id[b], id);
                    end
                    if (rmon_last[b] !== (b == ((burst == 2'b00) ? 0 : len))) begin
                        errors = errors + 1;
                        $display("FAIL rd beat%0d rlast=%b", b, rmon_last[b]);
                    end
                    wa = nxt(wa, burst, len);
                end
                resp = rmon_resp[0];
                if (bad > 0) errors = errors + 1;
            end
        end
    endtask

    reg [1:0] rs;
    reg [31:0] a32;
    reg [3:0] ln;
    reg [1:0] bs;
    integer e0;

    initial begin
        errors = 0;
        armon_n = 0; wmon_n = 0; bmon_n = 0; rmon_n = 0;
        for (i = 0; i < 256; i = i + 1) model[i] = pat(i[7:0]);
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        // t1: INCR write len=3 + readback
        e0 = errors;
        wr_burst(32'h0000_0100, 4'd3, 2'b01, 4'd2, 4'hF, -1, rs);
        if (rs !== 2'b00) begin errors = errors + 1; $display("FAIL t1a resp=%b", rs); end
        rd_burst(32'h0000_0100, 4'd3, 2'b01, 4'd2, rs);
        if (rs !== 2'b00) begin errors = errors + 1; $display("FAIL t1b resp=%b", rs); end
        if (errors == e0) $display("PASS t1: INCR len3 write+readback");

        // t2: WRAP len=3 (16B window) crossing boundary
        e0 = errors;
        wr_burst(32'h0000_0114, 4'd3, 2'b10, 4'd0, 4'hF, -1, rs);   // word 69, window 68..71
        if (rs !== 2'b00) begin errors = errors + 1; $display("FAIL t2a resp=%b", rs); end
        rd_burst(32'h0000_0114, 4'd3, 2'b10, 4'd0, rs);
        if (rs !== 2'b00) begin errors = errors + 1; $display("FAIL t2b resp=%b", rs); end
        if (errors == e0) $display("PASS t2: WRAP len3 write+readback");

        // t3: WRAP len=7 (32B window)
        e0 = errors;
        wr_burst(32'h0000_0204, 4'd7, 2'b10, 4'd3, 4'hF, -1, rs);   // word 129, window 128..135
        rd_burst(32'h0000_0204, 4'd7, 2'b10, 4'd3, rs);
        if (errors == e0) $display("PASS t3: WRAP len7");

        // t4: wstrb partial on INCR
        e0 = errors;
        wr_burst(32'h0000_0180, 4'd1, 2'b01, 4'd0, 4'h3, -1, rs);   // low halfword only
        rd_burst(32'h0000_0180, 4'd1, 2'b01, 4'd0, rs);
        if (errors == e0) $display("PASS t4: wstrb halfword");

        // t5: errors: FIXED write, early wlast, FIXED read, len0+wlast ok
        wr_burst(32'h0000_0300, 4'd3, 2'b00, 4'd0, 4'hF, -1, rs);
        if (rs !== 2'b10) begin errors = errors + 1; $display("FAIL t5a FIXED wr resp=%b", rs); end
        wr_burst(32'h0000_0340, 4'd3, 2'b01, 4'd0, 4'hF, 1, rs);    // wlast at beat 1 of 4
        if (rs !== 2'b10) begin errors = errors + 1; $display("FAIL t5b early-last resp=%b", rs); end
        rd_burst(32'h0000_0380, 4'd2, 2'b00, 4'd5, rs);
        if (rs !== 2'b10) begin errors = errors + 1; $display("FAIL t5c FIXED rd resp=%b", rs); end
        wr_burst(32'h0000_03C0, 4'd0, 2'b01, 4'd7, 4'hF, -1, rs);
        if (rs !== 2'b00) begin errors = errors + 1; $display("FAIL t5d len0 resp=%b", rs); end
        if (errors == e0) $display("PASS t5: error injections");

        // t6: out-of-order read completion (id=1 delayed vs id=0), via monitor order
        begin
            integer want_beats, c0_done, c1_done, order_first;
            e0 = errors;
            want_beats = 2;
            @(posedge clk); #1;
            rmon_n = 0;
            // AR id=1 (delayed 8 cycles)
            ar_issue(32'h0000_02C0, 4'd0, 2'b01, 4'd1);
            // AR id=0 (immediate)
            ar_issue(32'h0000_02C4, 4'd0, 2'b01, 4'd0);
            rready = 1;
            guard = 0;
            while (rmon_n < want_beats && guard < 40) begin
                @(posedge clk); #1; guard = guard + 1;
            end
            rready = 0;
            c0_done = 0; c1_done = 0;
            for (j = 0; j < rmon_n; j = j + 1) begin
                if (rmon_id[j] === 4'd0 && !c0_done) begin
                    c0_done = 1; order_first = 0;
                    if (rmon_data[j] !== model[32'h0000_02C4 >> 2]) begin
                        errors = errors + 1; $display("FAIL t6 id0 data %h", rmon_data[j]);
                    end
                end
                if (rmon_id[j] === 4'd1 && !c1_done) begin
                    c1_done = 1; order_first = 1;
                    if (rmon_data[j] !== model[32'h0000_02C0 >> 2]) begin
                        errors = errors + 1; $display("FAIL t6 id1 data %h", rmon_data[j]);
                    end
                end
            end
            if (c0_done && c1_done && order_first == 0) ;   // id0 first: OOO achieved
            else if (c0_done && c1_done) begin
                errors = errors + 1; $display("FAIL t6: no OOO (id1 completed first)");
            end else begin
                errors = errors + 1;
                $display("FAIL t6: completions id0=%0d id1=%0d", c0_done, c1_done);
            end
            if (errors == e0) $display("PASS t6: out-of-order read completion");
        end

        // t7: random burst stress vs model
        for (i = 0; i < 40; i = i + 1) begin
            bs = ($urandom_range(0, 3) < 2) ? 2'b01 : 2'b10;   // INCR or WRAP
            ln = (bs == 2'b10) ? ((4'b1 << $urandom_range(0, 2)) - 4'd1)  // wrap: len 0/1/3/7 (2^k window)
                              : $urandom_range(0, 7);
            a32 = {22'd0, $urandom_range(0, 255)} * 32'd4;      // word-aligned within 1KB
            if (bs == 2'b01 && (a32[9:2] + {4'd0, ln}) > 8'd252) bs = 2'b10; // keep INCR in range
            wr_burst(a32, ln, bs, $urandom_range(0, 7),
                     $urandom_range(1, 15), -1, rs);
            if (rs !== 2'b00) begin
                errors = errors + 1;
                $display("FAIL t7 random wr resp=%b burst=%b len=%0d addr=%h", rs, bs, ln, a32);
            end
            rd_burst(a32, ln, bs, $urandom_range(0, 7), rs);
            if (rs !== 2'b00) begin
                errors = errors + 1;
                $display("FAIL t7 random rd resp=%b", rs);
            end
        end
        $display("random bursts done");

        // t8: full-memory final compare via hierarchical unpacked array ref
        for (i = 0; i < 256; i = i + 1) begin
            if (dut.mem[i] !== model[i]) begin
                errors = errors + 1;
                $display("FAIL t8 mem[%0d]=%h want %h", i, dut.mem[i], model[i]);
            end
        end
        if (errors == 0) $display("PASS t8: full memory compare");

        if (errors == 0) $display("AXI4_TEST: ALL PASS");
        else             $display("AXI4_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
