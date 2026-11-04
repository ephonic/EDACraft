`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg  start = 0, sel = 0, div8 = 0;
    reg  [1:0] mode = 0;
    reg  [7:0] tx = 0;
    wire done;
    wire [7:0] rx;
    wire sck, mosi, busy;
    wire [1:0] ss_n;

    // loopback slave
    wire miso = mosi;

    spi_master dut (
        .clk(clk), .rst_n(rst_n), .start(start), .mode(mode), .div8(div8),
        .sel(sel), .tx(tx), .done(done), .rx(rx),
        .sck(sck), .mosi(mosi), .ss_n(ss_n), .miso(miso), .busy(busy)
    );

    always #5 clk = ~clk;

    integer errors, m, d, f, guard;
    reg [7:0] frames [0:4];
    reg sck_idle_ok;

    task automatic xfer(input [7:0] t, input integer exp_m, input integer exp_d);
        begin
            @(posedge clk); #1;
            mode = exp_m[1:0]; div8 = exp_d[0];
            start = 1; tx = t;
            @(posedge clk); #1; start = 0;
            guard = 0;
            while (!done && guard < 200) begin @(posedge clk); #1; guard = guard + 1; end
            if (!done) begin
                errors = errors + 1;
                $display("FAIL xfer %h mode=%0d div=%0d: timeout", t, exp_m, exp_d);
            end else if (rx !== t) begin
                errors = errors + 1;
                $display("FAIL xfer %h mode=%0d div=%0d: rx=%h", t, exp_m, exp_d, rx);
            end
            // after done, sck must sit at CPOL idle level
            #21;
            sck_idle_ok = (sck === exp_m[1]);
            if (!sck_idle_ok) begin
                errors = errors + 1;
                $display("FAIL idle sck=%b after mode=%0d", sck, exp_m);
            end
        end
    endtask

    initial begin
        errors = 0;
        frames[0] = 8'hA5; frames[1] = 8'h5A; frames[2] = 8'h00;
        frames[3] = 8'hFF; frames[4] = 8'h96;
        @(posedge clk); #1; @(posedge clk); #1; rst_n = 1;

        // all 4 modes x 2 dividers x 5 frames, alternating slave select
        for (m = 0; m < 4; m = m + 1) begin
            for (d = 0; d < 2; d = d + 1) begin
                for (f = 0; f < 5; f = f + 1) begin
                    sel = f[0];
                    xfer(frames[f], m, d);
                end
            end
        end
        $display("all mode/div/frame combos done");

        // ss check: during transfer selected low, idle both high
        if (ss_n !== 2'b11) begin
            errors = errors + 1;
            $display("FAIL ss_n=%b at idle", ss_n);
        end

        if (errors == 0) $display("SPI_TEST: ALL PASS");
        else             $display("SPI_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
