// SPI master: 8-bit frames, MSB first, 4 CPOL/CPHA modes, /4 //8 divider, 2 chip selects
`timescale 1ns/1ps
module spi_master (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire [1:0] mode,       // {CPOL, CPHA}
    input  wire       div8,       // 0: /4 (2 clk per half), 1: /8 (4 clk per half)
    input  wire       sel,        // slave select 0/1
    input  wire [7:0] tx,
    output reg        done,
    output reg  [7:0] rx,
    output wire       sck,
    output wire       mosi,
    output wire [1:0] ss_n,
    input  wire       miso,
    output wire       busy
);
    wire cpol = mode[1];
    wire cpha = mode[0];

    wire [1:0] half_max = div8 ? 2'd3 : 2'd1;

    typedef enum logic [1:0] { T_IDLE, T_RUN, T_TAIL } st_e;
    st_e st;

    reg [7:0] sh_tx, sh_rx;
    reg [2:0] bitc;
    reg [1:0] hcnt;
    reg       lead;      // next toggle is leading edge (first of pair)
    reg       sck_r;

    assign sck  = sck_r;
    assign mosi = sh_tx[7];
    assign ss_n = (st == T_IDLE) ? 2'b11 : (sel ? 2'b01 : 2'b10);
    assign busy = (st != T_IDLE);

    wire half_tick = (hcnt == half_max);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= T_IDLE; sck_r <= 1'b0; done <= 1'b0;
            sh_tx <= 8'd0; sh_rx <= 8'd0; bitc <= 3'd0; hcnt <= 2'd0; lead <= 1'b1;
        end else begin
            done <= 1'b0;
            unique case (st)
                T_IDLE: begin
                    sck_r <= cpol;                    // idle level follows CPOL
                    if (start) begin
                        sh_tx <= tx;
                        sh_rx <= 8'd0;
                        bitc  <= 3'd0;
                        hcnt  <= 2'd0;
                        lead  <= 1'b1;
                        sck_r <= cpol;
                        st    <= T_RUN;
                    end
                end
                T_RUN: begin
                    if (half_tick) begin
                        hcnt  <= 2'd0;
                        sck_r <= ~sck_r;              // toggle
                        if (lead) begin
                            // leading edge: CPHA=0 samples here; CPHA=1 data already stable
                            if (!cpha) sh_rx <= {sh_rx[6:0], miso};
                        end else begin
                            // trailing edge
                            if (!cpha) begin
                                sh_tx <= {sh_tx[6:0], 1'b0};   // CPHA=0: shift out
                            end else begin
                                sh_rx <= {sh_rx[6:0], miso};   // CPHA=1: sample
                                sh_tx <= {sh_tx[6:0], 1'b0};   // then next bit
                            end
                            if (bitc == 3'd7) begin
                                st <= T_TAIL;
                                hcnt <= 2'd0;
                            end
                            bitc <= bitc + 3'd1;
                        end
                        lead <= ~lead;
                    end else begin
                        hcnt <= hcnt + 2'd1;
                    end
                end
                T_TAIL: begin
                    // one extra half period of SS hold, sck returns to idle
                    if (half_tick) begin
                        sck_r <= cpol;
                        done   <= 1'b1;
                        rx     <= sh_rx;
                        st     <= T_IDLE;
                    end else begin
                        hcnt <= hcnt + 2'd1;
                    end
                end
            endcase
        end
    end
endmodule
