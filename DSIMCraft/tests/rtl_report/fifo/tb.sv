// task-free testbench (dsim 0.13.0 segfaults on task definitions)
`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    reg wr_en = 0, rd_en = 0;
    reg [7:0] wr_data = 0;
    wire [7:0] rd_data;
    wire full, empty, almost_full;
    wire [3:0] count;

    sync_fifo #(.WIDTH(8), .DEPTH(16), .ALMOST_FULL_THRESH(12)) dut (
        .clk(clk), .rst_n(rst_n), .wr_en(wr_en), .wr_data(wr_data),
        .rd_en(rd_en), .rd_data(rd_data), .full(full), .empty(empty),
        .almost_full(almost_full), .count(count)
    );

    always #5 clk = ~clk;

    integer i, errors;
    reg [7:0] expected;

    initial begin
        errors = 0;
        @(posedge clk); #1;
        @(posedge clk); #1;
        rst_n = 1;

        // Test 1: fill FIFO to full, check overflow protection
        for (i = 0; i < 20; i = i + 1) begin
            wr_en = 1; wr_data = 8'hA0 + i[7:0];
            @(posedge clk); #1;
        end
        wr_en = 0;
        if (full !== 1'b1) begin errors = errors + 1; $display("FAIL t1: not full after 20 writes, count=%0d", count); end
        else $display("PASS t1: full asserted, count=%0d", count);

        // Test 2: drain FIFO, verify order and content
        for (i = 0; i < 16; i = i + 1) begin
            rd_en = 1; @(posedge clk); #1;
            expected = 8'hA0 + i[7:0];
            if (rd_data !== expected) begin
                errors = errors + 1;
                $display("FAIL t2: read[%0d]=%h expected %h", i, rd_data, expected);
            end
        end
        rd_en = 0;
        @(posedge clk); #1;
        if (empty !== 1'b1) begin errors = errors + 1; $display("FAIL t2: not empty after drain, count=%0d", count); end
        else $display("PASS t2: drained in order, empty asserted");

        // Test 3: read from empty (underflow protection)
        rd_en = 1; @(posedge clk); #1; @(posedge clk); #1; @(posedge clk); #1;
        rd_en = 0;
        if (empty !== 1'b1) begin errors = errors + 1; $display("FAIL t3: empty flag lost on underflow read"); end
        else $display("PASS t3: empty read ignored");

        // Test 4: simultaneous read/write at full boundary
        for (i = 0; i < 16; i = i + 1) begin
            wr_en = 1; wr_data = 8'h50 + i[7:0]; @(posedge clk); #1;
        end
        wr_en = 1; wr_data = 8'hEE; rd_en = 1;
        @(posedge clk); #1;
        wr_en = 0; rd_en = 0;
        @(posedge clk); #1;
        if (rd_data !== 8'h50) begin errors = errors + 1; $display("FAIL t4: got %h expected 50", rd_data); end
        else $display("PASS t4: full-boundary rd/wr handled");

        // Test 5: simultaneous rd+wr on empty fifo: write lands, read blocked this cycle, data readable next cycle
        rst_n = 0; @(posedge clk); #1; rst_n = 1; @(posedge clk); #1;
        wr_en = 1; wr_data = 8'h77; rd_en = 1;
        @(posedge clk); #1;
        wr_en = 0; rd_en = 1;
        @(posedge clk); #1;
        rd_en = 0;
        if (rd_data !== 8'h77) begin errors = errors + 1; $display("FAIL t5: got %h expected 77", rd_data); end
        else $display("PASS t5: write-then-read on refilled fifo");

        // Test 6: almost_full threshold
        rst_n = 0; @(posedge clk); #1; rst_n = 1; @(posedge clk); #1;
        for (i = 0; i < 12; i = i + 1) begin
            wr_en = 1; wr_data = i[7:0]; @(posedge clk); #1;
        end
        wr_en = 0;
        if (almost_full !== 1'b1) begin errors = errors + 1; $display("FAIL t6: almost_full not set at count=%0d", count); end
        else $display("PASS t6: almost_full at count=%0d", count);

        if (errors == 0) $display("FIFO_TEST: ALL PASS");
        else $display("FIFO_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
