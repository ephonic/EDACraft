// UART TX testbench: low-speed emulation (small DIVISOR) + software UART receiver decoder
`timescale 1ns/1ps
module tb;
    // override via smaller clocks so sim is fast: 8 ticks per bit
    localparam DIV = 8;

    reg clk = 0, rst_n = 0, start = 0;
    reg [7:0] data = 0;
    wire tx, busy, done;

    uart_tx #(.CLK_FREQ(DIV), .BAUD(1), .PARITY(1)) dut (
        .clk(clk), .rst_n(rst_n), .data(data), .start(start),
        .tx(tx), .busy(busy), .done(done)
    );

    always #5 clk = ~clk;

    integer errors, i;
    reg [7:0] sent [0:9];
    reg [7:0] recv_data;
    reg recv_par;

    // software receiver: sample at mid-bit
    integer bit_cnt;
    initial begin
        errors = 0;
        for (i = 0; i < 10; i = i + 1) sent[i] = 8'h41 + i[7:0]*3;

        @(posedge clk); #1; rst_n = 1; #1;

        for (i = 0; i < 10; i = i + 1) begin
            // wait idle
            while (busy) @(posedge clk);
            #1;

            // drive start
            data = sent[i]; start = 1;
            @(posedge clk); #1;
            start = 0;

            // wait for falling edge of tx = start bit begins
            @(negedge tx);
            // sample mid start bit
            repeat (DIV/2) @(posedge clk);
            if (tx !== 1'b0) begin errors++; $display("FAIL byte%0d: start bit not 0", i); end

            // sample 8 data bits
            for (bit_cnt = 0; bit_cnt < 8; bit_cnt = bit_cnt + 1) begin
                repeat (DIV) @(posedge clk);
                recv_data[bit_cnt] = tx;
            end
            // parity bit
            repeat (DIV) @(posedge clk);
            recv_par = tx;
            // stop bit
            repeat (DIV) @(posedge clk);
            if (tx !== 1'b1) begin errors++; $display("FAIL byte%0d: stop bit not 1", i); end

            if (recv_data !== sent[i]) begin
                errors++;
                $display("FAIL byte%0d: recv=%b sent=%b", i, recv_data, sent[i]);
            end
            if (recv_par !== ^sent[i]) begin
                errors++;
                $display("FAIL byte%0d: parity recv=%b exp=%b", i, recv_par, ^sent[i]);
            end
        end

        // wait for done pulse of last byte
        @(posedge clk); #1;
        while (!done && busy) @(posedge clk);

        if (errors == 0) $display("UART_TEST: ALL PASS (10 bytes, 8N1+even parity)");
        else $display("UART_TEST: %0d ERRORS", errors);
        $finish;
    end
endmodule
