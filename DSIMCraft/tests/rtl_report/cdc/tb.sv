`timescale 1ns/1ps
module tb;
    // write clock 100MHz, read clock 66MHz (asynchronous ratio)
    reg wclk = 0, rclk = 0;
    always #5 wclk = ~wclk;    // 10ns period
    always #7.5 rclk = ~rclk;  // 15ns period

    reg wrst_n = 0, rrst_n = 0;
    reg w_en = 0, r_en = 0;
    reg [7:0] w_data = 0;
    wire [7:0] r_data;
    wire full, empty;

    cdc_async_fifo #(.WIDTH(8), .DEPTH(8)) dut (
        .wclk(wclk), .wrst_n(wrst_n), .w_en(w_en), .w_data(w_data),
        .rclk(rclk), .rrst_n(rrst_n), .r_en(r_en), .r_data(r_data),
        .full(full), .empty(empty)
    );

    // pulse synchronizer under test
    reg src_pulse = 0;
    wire dst_pulse;
    pulse_sync psync(.src_clk(wclk), .src_rst_n(wrst_n), .src_pulse(src_pulse),
                     .dst_clk(rclk), .dst_rst_n(rrst_n), .dst_pulse(dst_pulse));

    integer errors, i;
    integer sent, recvd;
    reg [7:0] q [0:255];
    integer pulse_out_cnt, pulse_in_cnt;

    // read-side consumer: read whenever not empty (with random-ish gaps via mod)
    initial begin
        r_en = 0;
        forever begin
            @(posedge rclk);
            #1;
            r_en = (recvd < sent) && (((recvd + 2) % 5) != 0); // intermittent reads
        end
    end

    // read-side consumer: read whenever not empty (with intermittent gaps)
    integer cyc;
    initial begin
        r_en = 0; cyc = 0;
        forever begin
            @(posedge rclk);
            #1;
            cyc = cyc + 1;
            r_en = (recvd < sent) && ((cyc % 5) != 3); // intermittent reads
        end
    end

    // read data checker (r_data is registered: compare one cycle after accept)
    reg prev_accept;
    always @(posedge rclk) begin
        if (rrst_n && prev_accept) begin
            if (r_data !== q[recvd][7:0]) begin
                errors = errors + 1;
                $display("FAIL cdc: recv[%0d]=%h expected %h", recvd, r_data, q[recvd]);
            end
            recvd = recvd + 1;
        end
        prev_accept <= rrst_n && r_en && !empty;
    end

    // count pulse_sync outputs
    always @(posedge rclk) if (rrst_n && dst_pulse) pulse_out_cnt = pulse_out_cnt + 1;

    initial begin
        errors = 0; sent = 0; recvd = 0;
        pulse_in_cnt = 0; pulse_out_cnt = 0;

        // async reset release (staggered, as in real CDC)
        repeat (3) @(posedge wclk); wrst_n = 1;
        repeat (3) @(posedge rclk); rrst_n = 1;
        repeat (5) @(posedge wclk);

        // write 200 bytes with gaps, bursts
        for (i = 0; i < 200; i = i + 1) begin
            if ((i % 11) == 5) begin
                w_en = 0;                       // gap cycle
                @(posedge wclk); #1;
            end else begin
                @(posedge wclk); #1;
                while (full) begin              // wait for space
                    @(posedge wclk); #1;
                end
                w_en = 1;
                w_data = 8'h10 + i[7:0];
                q[sent] = 8'h10 + i[7:0];
                sent = sent + 1;
                if ((i % 17) == 0) begin
                    src_pulse = 1; pulse_in_cnt = pulse_in_cnt + 1;
                end
                @(posedge wclk); #1;
                w_en = 0; src_pulse = 0;
            end
        end

        // drain: wait until all read
        i = 0;
        while (recvd < sent && i < 5000) begin
            @(posedge rclk); i = i + 1;
        end

        if (recvd != sent) begin
            errors = errors + 1;
            $display("FAIL cdc: sent=%0d recvd=%0d (data lost/stuck)", sent, recvd);
        end else
            $display("PASS cdc: %0d bytes transferred across domains in order", sent);

        repeat (20) @(posedge rclk);
        if (pulse_out_cnt !== pulse_in_cnt) begin
            errors = errors + 1;
            $display("FAIL pulse_sync: in=%0d out=%0d", pulse_in_cnt, pulse_out_cnt);
        end else
            $display("PASS pulse_sync: %0d pulses transferred", pulse_out_cnt);

        if (errors == 0) $display("CDC_TEST: ALL PASS");
        else $display("CDC_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
