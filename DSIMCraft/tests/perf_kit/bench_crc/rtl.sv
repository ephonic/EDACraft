// streaming CRC-32 (reflected, poly 0xEDB88320), 1 byte/cycle, SOF/EOF framing
`timescale 1ns/1ps
module crc32_engine (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        soc,        // start of frame (with first valid byte)
    input  wire        eoc,        // end of frame (with last valid byte)
    input  wire        valid,
    input  wire [7:0]  data_in,
    output reg         crc_valid,  // 1-cycle pulse after eoc
    output reg  [31:0] crc_out,
    output wire        busy
);
    reg        in_frame;
    reg [31:0] crc;
    assign busy = in_frame;

    function automatic [31:0] crc_byte(input [31:0] c, input [7:0] d);
        integer i;
        reg [31:0] t;
        begin
            t = c ^ {24'd0, d};
            for (i = 0; i < 8; i = i + 1)
                t = (t >> 1) ^ (32'hEDB88320 & {32{t[0]}});
            crc_byte = t;
        end
    endfunction

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_frame <= 1'b0; crc <= 32'hFFFFFFFF;
            crc_valid <= 1'b0; crc_out <= 32'd0;
        end else begin
            crc_valid <= 1'b0;
            if (valid) begin
                if (soc) begin
                    crc <= crc_byte(32'hFFFFFFFF, data_in);
                    in_frame <= !eoc;      // single-byte frame case
                    if (eoc) begin
                        crc_out   <= crc_byte(32'hFFFFFFFF, data_in) ^ 32'hFFFFFFFF;
                        crc_valid <= 1'b1;
                    end
                end else if (in_frame) begin
                    crc <= crc_byte(crc, data_in);
                    if (eoc) begin
                        crc_out   <= crc_byte(crc, data_in) ^ 32'hFFFFFFFF;
                        crc_valid <= 1'b1;
                        in_frame  <= 1'b0;
                    end
                end
            end
        end
    end
endmodule
