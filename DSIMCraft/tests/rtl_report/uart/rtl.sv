// UART transmitter: FSM (IDLE/START/DATA/PARITY/STOP), baud counter, shift register
`timescale 1ns/1ps
module uart_tx #(
    parameter CLK_FREQ = 50_000_000,
    parameter BAUD     = 115200,
    parameter PARITY   = 1   // 0:none 1:even
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] data,
    input  wire       start,
    output reg        tx,
    output reg        busy,
    output reg        done
);
    localparam DIVISOR = CLK_FREQ / BAUD;

    localparam [2:0] S_IDLE = 3'd0, S_START = 3'd1, S_DATA = 3'd2,
                     S_PAR  = 3'd3, S_STOP  = 3'd4;

    reg [2:0]  state;
    reg [15:0] baud_cnt;
    reg [2:0]  bit_idx;
    reg [7:0]  shifter;
    reg        par_bit;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; tx <= 1'b1; busy <= 1'b0; done <= 1'b0;
            baud_cnt <= 0; bit_idx <= 0; shifter <= 0; par_bit <= 0;
        end else begin
            done <= 1'b0;
            case (state)
                S_IDLE: begin
                    tx <= 1'b1;
                    if (start) begin
                        shifter  <= data;
                        par_bit  <= ^data;
                        busy     <= 1'b1;
                        baud_cnt <= 0;
                        state    <= S_START;
                    end
                end
                S_START: begin
                    tx <= 1'b0;
                    if (baud_cnt == DIVISOR-1) begin
                        baud_cnt <= 0;
                        bit_idx  <= 0;
                        state    <= S_DATA;
                    end else baud_cnt <= baud_cnt + 1'b1;
                end
                S_DATA: begin
                    tx <= shifter[bit_idx];
                    if (baud_cnt == DIVISOR-1) begin
                        baud_cnt <= 0;
                        if (bit_idx == 3'd7) state <= PARITY ? S_PAR : S_STOP;
                        else bit_idx <= bit_idx + 1'b1;
                    end else baud_cnt <= baud_cnt + 1'b1;
                end
                S_PAR: begin
                    tx <= par_bit;
                    if (baud_cnt == DIVISOR-1) begin
                        baud_cnt <= 0;
                        state <= S_STOP;
                    end else baud_cnt <= baud_cnt + 1'b1;
                end
                S_STOP: begin
                    tx <= 1'b1;
                    if (baud_cnt == DIVISOR-1) begin
                        baud_cnt <= 0;
                        busy <= 1'b0;
                        done <= 1'b1;
                        state <= S_IDLE;
                    end else baud_cnt <= baud_cnt + 1'b1;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
