// Synchronous FIFO with parameterizable depth/width
// Tests: memory array, pointer wrap arithmetic, full/empty flags, almost_full
`timescale 1ns/1ps
module sync_fifo #(
    parameter WIDTH = 8,
    parameter DEPTH = 16,
    parameter ALMOST_FULL_THRESH = 12
)(
    input  wire             clk,
    input  wire             rst_n,
    input  wire             wr_en,
    input  wire [WIDTH-1:0] wr_data,
    input  wire             rd_en,
    output reg  [WIDTH-1:0] rd_data,
    output wire             full,
    output wire             empty,
    output wire             almost_full,
    output wire [3:0]       count
);
    localparam AW = $clog2(DEPTH);

    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [AW:0] wptr, rptr;

    assign full       = (wptr[AW] != rptr[AW]) && (wptr[AW-1:0] == rptr[AW-1:0]);
    assign empty      = (wptr == rptr);
    assign almost_full = (count >= ALMOST_FULL_THRESH);
    assign count      = wptr[AW-1:0] - rptr[AW-1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wptr <= 0;
        end else if (wr_en && !full) begin
            mem[wptr[AW-1:0]] <= wr_data;
            wptr <= wptr + 1'b1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rptr  <= 0;
            rd_data <= 0;
        end else if (rd_en && !empty) begin
            rd_data <= mem[rptr[AW-1:0]];
            rptr    <= rptr + 1'b1;
        end
    end
endmodule
