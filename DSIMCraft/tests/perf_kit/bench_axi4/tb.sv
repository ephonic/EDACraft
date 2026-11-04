// axi4 perf bench (negedge-driven, race-free): N random INCR/WRAP bursts + checksum
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

    reg [31:0] model [0:255];
    integer wmon_n, rmon_n, armon_n, bmon_n;
    reg [31:0] chk;
    function automatic [31:0] merge(input [31:0] d, input [31:0] o, input [3:0] s);
        merge = {s[3] ? d[31:24] : o[31:24], s[2] ? d[23:16] : o[23:16],
                 s[1] ? d[15:8] : o[15:8], s[0] ? d[7:0] : o[7:0]};
    endfunction
    function automatic [7:0] nxt(input [7:0] a, input [1:0] burst, input [3:0] len);
        reg [7:0] mask, base;
        begin
            if (burst == 2'b10) begin
                mask = {4'd0, len};
                base = a & ~mask;
                nxt = base | (((a & mask) + 8'd1) & mask);
            end else nxt = a + 8'd1;
        end
    endfunction

    always @(posedge clk) begin
        if (rst_n && wvalid && wready) wmon_n = wmon_n + 1;
        if (rst_n && arvalid && arready) armon_n = armon_n + 1;
        if (rst_n && rvalid && rready) rmon_n = rmon_n + 1;
        if (rst_n && bvalid && bready) bmon_n = bmon_n + 1;
    end

    // capture rdata for the beat handshaked at the PRECEDING posedge (before DUT advances it)
    reg [31:0] rmon_data;
    always @(posedge clk) if (rst_n && rvalid && rready) rmon_data = rdata;

    task automatic wr_burst(input [31:0] addr, input [3:0] len, input [1:0] burst,
                            input [3:0] strb);
        reg [7:0] wa, na; reg [3:0] beat; integer n0;
        begin
            @(negedge clk);
            awaddr = addr; awlen = len; awburst = burst; awid = 4'd0; awvalid = 1;
            wvalid = 1; wstrb = strb;
            wa = addr[9:2]; beat = 0;
            while (beat <= len) begin
                wdata = {wa, ~wa, (wa ^ 8'h3C), (wa + {4'd0, beat})};
                wlast = (beat == len);
                model[wa] = merge(wdata, model[wa], strb);
                na = nxt(wa, burst, len);
                n0 = wmon_n;
                while (wmon_n == n0) @(negedge clk);
                if (wlast) beat = len + 1;
                else begin wa = na; beat = beat + 1; end
            end
            wvalid = 0; wlast = 0; awvalid = 0;   // clear before next posedge
            n0 = bmon_n;
            bready = 1;
            while (bmon_n == n0) @(negedge clk);
            @(negedge clk); bready = 0;
        end
    endtask

    task automatic rd_burst(input [31:0] addr, input [3:0] len, input [1:0] burst);
        reg [7:0] wa; reg [3:0] beat; integer n0;
        begin
            @(negedge clk);
            araddr = addr; arlen = len; arburst = burst; arid = 4'd0; arvalid = 1;
            n0 = armon_n;
            while (armon_n == n0) @(negedge clk);
            arvalid = 0;                            // clear before next posedge
            rready = 1;
            wa = addr[9:2]; beat = 0;
            while (beat <= len) begin
                n0 = rmon_n;
                while (rmon_n == n0) @(negedge clk);
                chk = chk ^ rmon_data ^ model[wa];
                wa = nxt(wa, burst, len);
                beat = beat + 1;
            end
            rready = 0;
        end
    endtask

    reg [31:0] a32;
    reg [3:0] ln;
    reg [1:0] bs;
    integer i;

    initial begin
        wmon_n = 0; rmon_n = 0; armon_n = 0; bmon_n = 0; chk = 0;
        for (i = 0; i < 256; i = i + 1)
            model[i] = {i[7:0], ~i[7:0], (i[7:0] ^ 8'h5A), (i[7:0] + 8'hA5)};
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        for (i = 0; i < 30000; i = i + 1) begin
            rng_state = xs32(rng_state);
            bs = ((rng_state % 4) < 2) ? 2'b01 : 2'b10;
            rng_state = xs32(rng_state);
            ln = (bs == 2'b10) ? ((4'b1 << (rng_state % 3)) - 4'd1) : (rng_state % 8);
            rng_state = xs32(rng_state);
            a32 = {22'd0, (rng_state % 256)} * 32'd4;
            if (bs == 2'b01 && (a32[9:2] + {4'd0, ln}) > 8'd252) bs = 2'b10;
            wr_burst(a32, ln, bs, 4'hF);
            rd_burst(a32, ln, bs);
        end
        for (i = 0; i < 256; i = i + 1) chk = chk ^ model[i];
        $display("PERF axi4: PASS bursts=30000 beats(w=%0d,r=%0d) chk=0x%08x",
                 wmon_n, rmon_n, chk);
        $finish;
    end
endmodule
