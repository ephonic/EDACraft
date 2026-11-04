// Dual-clock async FIFO (Gray-coded pointers, Cummings-style registered flags)
// + 2-flop synchronizer + pulse synchronizer
`timescale 1ns/1ps
module cdc_async_fifo #(
    parameter WIDTH = 8,
    parameter DEPTH = 8
)(
    input  wire             wclk,
    input  wire             wrst_n,
    input  wire             w_en,
    input  wire [WIDTH-1:0] w_data,
    input  wire             rclk,
    input  wire             rrst_n,
    input  wire             r_en,
    output reg  [WIDTH-1:0] r_data,
    output reg              full,
    output reg              empty
);
    localparam AW = $clog2(DEPTH);

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    function [AW:0] gray2bin(input [AW:0] g);
        integer i;
        begin
            gray2bin[AW] = g[AW];
            for (i = AW-1; i >= 0; i = i - 1)
                gray2bin[i] = gray2bin[i+1] ^ g[i];
        end
    endfunction

    function [AW:0] bin2gray(input [AW:0] b);
        begin
            bin2gray = (b >> 1) ^ b;
        end
    endfunction

    // write domain pointers
    reg [AW:0] wbin, wgray;
    wire       waccept = w_en && !full;
    wire [AW:0] wnext_bin  = wbin + waccept;
    wire [AW:0] wnext_gray = bin2gray(wnext_bin);

    // read domain pointers
    reg [AW:0] rbin, rgray;
    wire       raccept = r_en && !empty;
    wire [AW:0] rnext_bin  = rbin + raccept;
    wire [AW:0] rnext_gray = bin2gray(rnext_bin);

    // synchronizers
    reg [AW:0] wgray_sync1, wgray_sync2;   // wr ptr into read domain
    reg [AW:0] rgray_sync1, rgray_sync2;   // rd ptr into write domain

    // write domain
    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wbin <= 0; wgray <= 0; full <= 0;
            rgray_sync1 <= 0; rgray_sync2 <= 0;
        end else begin
            rgray_sync1 <= rgray;
            rgray_sync2 <= rgray_sync1;
            if (waccept) begin
                mem[wnext_bin[AW-1:0]] <= w_data;
                wbin  <= wnext_bin;
                wgray <= wnext_gray;
            end
            full <= (wnext_gray == {~rgray_sync2[AW:AW-1], rgray_sync2[AW-2:0]});
        end
    end

    // read domain
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rbin <= 0; rgray <= 0; empty <= 1;
            wgray_sync1 <= 0; wgray_sync2 <= 0;
            r_data <= 0;
        end else begin
            wgray_sync1 <= wgray;
            wgray_sync2 <= wgray_sync1;
            if (raccept) begin
                r_data <= mem[rnext_bin[AW-1:0]];
                rbin   <= rnext_bin;
                rgray  <= rnext_gray;
            end
            empty <= (rnext_gray == wgray_sync2);
        end
    end
endmodule

// pulse synchronizer: toggle + 2FF + edge detect
module pulse_sync (
    input  wire src_clk,
    input  wire src_rst_n,
    input  wire src_pulse,
    input  wire dst_clk,
    input  wire dst_rst_n,
    output wire  dst_pulse
);
    reg toggle;
    always @(posedge src_clk or negedge src_rst_n) begin
        if (!src_rst_n) toggle <= 1'b0;
        else if (src_pulse) toggle <= ~toggle;
    end
    reg sync1, sync2, sync3;
    always @(posedge dst_clk or negedge dst_rst_n) begin
        if (!dst_rst_n) begin sync1 <= 0; sync2 <= 0; sync3 <= 0; end
        else begin sync1 <= toggle; sync2 <= sync1; sync3 <= sync2; end
    end
    assign dst_pulse = sync2 ^ sync3;
endmodule
