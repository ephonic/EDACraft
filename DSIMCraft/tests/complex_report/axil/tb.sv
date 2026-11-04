`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg [31:0] awaddr = 0; reg awvalid = 0; wire awready;
    reg [31:0] wdata = 0;  reg [3:0] wstrb = 0; reg wvalid = 0; wire wready;
    wire bvalid; reg bready = 0; wire [1:0] bresp;
    reg [31:0] araddr = 0; reg arvalid = 0; wire arready;
    wire rvalid; reg rready = 0; wire [31:0] rdata; wire [1:0] rresp;
    reg event_in = 0;

    axil_slave dut (
        .clk(clk), .rst_n(rst_n), .event_in(event_in),
        .awaddr(awaddr), .awprot(3'b0), .awvalid(awvalid), .awready(awready),
        .wdata(wdata), .wstrb(wstrb), .wvalid(wvalid), .wready(wready),
        .bvalid(bvalid), .bready(bready), .bresp(bresp),
        .araddr(araddr), .arprot(3'b0), .arvalid(arvalid), .arready(arready),
        .rvalid(rvalid), .rready(rready), .rdata(rdata), .rresp(rresp)
    );

    always #5 clk = ~clk;

    integer errors;
    integer i;

    task automatic rand_delay;
        integer d, j;
        begin
            d = $urandom_range(0, 4);
            for (j = 0; j < d; j = j + 1) @(posedge clk);
        end
    endtask

    task automatic axil_write(input [31:0] addr, input [31:0] data, input [3:0] strb,
                              output [1:0] resp);
        begin
            @(posedge clk); #1;
            awaddr = addr; awvalid = 1;
            wdata = data; wstrb = strb; wvalid = 1;
            bready = 0;
            while (!(awready === 1'b1 && wready === 1'b1)) @(posedge clk);
            @(posedge clk); #1;            // acceptance edge
            awvalid = 0; wvalid = 0;
            rand_delay();                  // slave must hold bvalid
            bready = 1;
            while (bvalid !== 1'b1) @(posedge clk);
            @(posedge clk); #1;            // B handshake edge
            resp = bresp;
            bready = 0;
        end
    endtask

    task automatic axil_read(input [31:0] addr, output [31:0] data, output [1:0] resp);
        begin
            @(posedge clk); #1;
            araddr = addr; arvalid = 1;
            rready = 0;
            while (arready !== 1'b1) @(posedge clk);
            @(posedge clk); #1;            // acceptance edge
            arvalid = 0;
            rand_delay();                  // slave must hold rvalid
            rready = 1;
            while (rvalid !== 1'b1) @(posedge clk);
            @(posedge clk); #1;            // R handshake edge
            data = rdata; resp = rresp;
            rready = 0;
        end
    endtask

    reg [31:0] rd;
    reg [1:0]  rs;
    reg [31:0] cnt_a, cnt_b;

    initial begin
        errors = 0;
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        // t1: full-word write + readback (bit0=0 keeps counter disabled)
        axil_write(32'h0000_0000, 32'hDEAD_BEEE, 4'hF, rs);
        if (rs !== 2'b00) begin errors = errors + 1; $display("FAIL t1a: resp=%b", rs); end
        axil_read(32'h0000_0000, rd, rs);
        if (rd !== 32'hDEAD_BEEE || rs !== 2'b00) begin
            errors = errors + 1; $display("FAIL t1b: rd=%h resp=%b", rd, rs);
        end else $display("PASS t1: scr0 write/readback");

        // t2: WSTRB partial write on scr1 (upper byte only)
        axil_write(32'h0000_0004, 32'h12345678, 4'h1, rs);   // byte0 only
        axil_read(32'h0000_0004, rd, rs);
        if (rd !== 32'h00000078) begin
            errors = errors + 1; $display("FAIL t2a: rd=%h", rd);
        end
        axil_write(32'h0000_0004, 32'hAB000000, 4'h8, rs);   // byte3 only
        axil_read(32'h0000_0004, rd, rs);
        if (rd !== 32'hAB000078) begin
            errors = errors + 1; $display("FAIL t2b: rd=%h", rd);
        end else $display("PASS t2: WSTRB lane merge");

        // t3: RO counter, gated by scr0[0]
        axil_read(32'h0000_0008, rd, rs); cnt_a = rd;      // disabled: reads same
        axil_read(32'h0000_0008, rd, rs);
        if (rd !== cnt_a) begin
            errors = errors + 1; $display("FAIL t3a: counter ran while disabled %0d -> %0d", cnt_a, rd);
        end
        axil_write(32'h0000_0000, 32'h0000_0001, 4'hF, rs); // enable
        repeat (3) @(posedge clk);
        axil_read(32'h0000_0008, rd, rs); cnt_a = rd;
        axil_read(32'h0000_0008, rd, rs); cnt_b = rd;
        if (cnt_b <= cnt_a || cnt_b - cnt_a > 20) begin
            errors = errors + 1; $display("FAIL t3b: counter delta %0d", cnt_b - cnt_a);
        end else $display("PASS t3: counter enabled, delta=%0d", cnt_b - cnt_a);
        axil_write(32'h0000_0000, 32'h0000_0000, 4'hF, rs); // disable

        // t4: RW1C sticky. bit0 = event, bit1 = cnt==0x80
        axil_write(32'h0000_000C, 32'h0000_0003, 4'hF, rs); // clear any residue
        axil_read(32'h0000_000C, rd, rs);
        if (rd[1:0] !== 2'b00) begin errors = errors + 1; $display("FAIL t4a: sticky=%b", rd[1:0]); end
        event_in = 1; @(posedge clk); #1; event_in = 0;
        repeat (2) @(posedge clk);
        axil_read(32'h0000_000C, rd, rs);
        if (rd[1:0] !== 2'b01) begin
            errors = errors + 1; $display("FAIL t4b: sticky=%b (want 01)", rd[1:0]);
        end else begin
            axil_write(32'h0000_000C, 32'h0000_0001, 4'hF, rs); // clear bit0
            axil_read(32'h0000_000C, rd, rs);
            if (rd[1:0] !== 2'b00) begin
                errors = errors + 1; $display("FAIL t4c: sticky=%b after RW1C", rd[1:0]);
            end else $display("PASS t4: event sticky + RW1C clear");
        end

        // t5: SLVERR on unmapped write/read
        axil_write(32'h0000_0100, 32'h0, 4'hF, rs);
        if (rs !== 2'b10) begin errors = errors + 1; $display("FAIL t5a: wr resp=%b", rs); end
        axil_read(32'h0000_0FFC, rd, rs);
        if (rs !== 2'b10) begin errors = errors + 1; $display("FAIL t5b: rd resp=%b", rs); end
        axil_write(32'h0000_0010, 32'h0, 4'hF, rs);        // mapped region hole (0x10)
        if (rs !== 2'b10) begin errors = errors + 1; $display("FAIL t5c: rd resp=%b", rs); end
        else $display("PASS t5: SLVERR unmapped/hole");

        // t6: bus still healthy after SLVERR
        axil_write(32'h0000_0000, 32'hCAFE0000, 4'hF, rs);
        axil_read(32'h0000_0000, rd, rs);
        if (rd !== 32'hCAFE0000) begin errors = errors + 1; $display("FAIL t6: rd=%h", rd); end
        else $display("PASS t6: bus recovery after SLVERR");

        // t7: random stress — 32 random legal writes w/ random strb, verify via shadow model
        begin
            reg [31:0] shadow0, shadow1;
            shadow0 = 32'hCAFE0000; shadow1 = 32'hAB000078;
            for (i = 0; i < 32; i = i + 1) begin
                reg [31:0] a, d; reg [3:0] s;
                a = ({$urandom} % 2 == 0) ? 32'h0 : 32'h4;
                d = $urandom;
                s = $urandom_range(1, 15);
                axil_write(a, d, s, rs);
                if (a[3:2] == 2'd0)
                    shadow0 = {s[3] ? d[31:24] : shadow0[31:24], s[2] ? d[23:16] : shadow0[23:16], s[1] ? d[15:8] : shadow0[15:8], s[0] ? d[7:0] : shadow0[7:0]};
                if (a[3:2] == 2'd1)
                    shadow1 = {s[3] ? d[31:24] : shadow1[31:24], s[2] ? d[23:16] : shadow1[23:16], s[1] ? d[15:8] : shadow1[15:8], s[0] ? d[7:0] : shadow1[7:0]};
            end
            axil_read(32'h0000_0000, rd, rs);
            if (rd !== shadow0) begin errors = errors + 1; $display("FAIL t7a: rd=%h shadow=%h", rd, shadow0); end
            axil_read(32'h0000_0004, rd, rs);
            if (rd !== shadow1) begin errors = errors + 1; $display("FAIL t7b: rd=%h shadow=%h", rd, shadow1); end
            if (errors == 0) $display("PASS t7: 32 random-strb writes match shadow");
        end

        if (errors == 0) $display("AXIL_TEST: ALL PASS");
        else             $display("AXIL_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
