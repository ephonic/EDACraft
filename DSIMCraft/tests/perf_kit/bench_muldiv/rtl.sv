// iterative signed 16x16 Booth radix-4 multiplier + 32/16 restoring divider
`timescale 1ns/1ps
module booth_mul16 (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               start,
    input  wire signed [15:0] a,
    input  wire signed [15:0] b,
    output wire               busy,
    output reg                done,
    output reg signed [31:0]  product
);
    typedef enum logic [1:0] { S_IDLE, S_RUN, S_DONE } st_e;
    st_e st;
    assign busy = (st != S_IDLE);

    reg        [31:0] acc;
    reg        [3:0]  idx;   // 8 steps of 2 bits
    reg signed [15:0] bsh;   // remaining multiplier bits (LSB-first consumption)
    reg               prev;  // booth overlap bit
    reg signed [31:0] d_ext;

    function automatic signed [31:0] pp(input signed [31:0] d, input [2:0] win);
        case (win)
            3'b000, 3'b111:  pp = 32'sd0;
            3'b001, 3'b010:  pp = d;
            3'b011:          pp = d <<< 1;
            3'b100:          pp = -(d <<< 1);
            3'b101, 3'b110:  pp = -d;
            default:         pp = 32'sd0;
        endcase
    endfunction

    wire [2:0] win = {bsh[1:0], prev};

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; acc <= 32'd0; idx <= 4'd0; done <= 1'b0;
            product <= 32'sd0; bsh <= 16'sd0; prev <= 1'b0; d_ext <= 32'sd0;
        end else begin
            done <= 1'b0;
            unique case (st)
                S_IDLE: if (start) begin
                    acc   <= 32'd0;
                    idx   <= 4'd0;
                    bsh   <= b;
                    prev  <= 1'b0;
                    d_ext <= $signed({{16{a[15]}}, a});
                    st    <= S_RUN;
                end
                S_RUN: begin
                    acc  <= acc + (pp(d_ext, win) <<< (2 * idx));
                    prev <= bsh[1];
                    bsh  <= bsh >>> 2;
                    idx  <= idx + 4'd1;
                    if (idx == 4'd7) st <= S_DONE;
                end
                S_DONE: begin
                    done    <= 1'b1;
                    product <= acc;
                    st      <= S_IDLE;
                end
            endcase
        end
    end
endmodule

module udiv32_16 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,
    input  wire [31:0] dvd,
    input  wire [15:0] dvs,
    output wire        busy,
    output reg         done,
    output reg  [31:0] quo,
    output reg  [15:0] rem_o
);
    typedef enum logic [1:0] { D_IDLE, D_RUN, D_DONE } st_e;
    st_e st;
    assign busy = (st != D_IDLE);

    reg [31:0] q;
    reg [31:0] d;    // remaining dividend, MSB-first
    reg [16:0] r;    // 17-bit working remainder
    reg [5:0]  cnt;

    wire [17:0] rnext = {r, d[31]};                 // shift in next dividend bit
    wire sub_ok = (rnext >= {1'b0, dvs}) && (dvs != 16'd0);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= D_IDLE; q <= 32'd0; d <= 32'd0; r <= 17'd0; cnt <= 6'd0;
            done <= 1'b0; quo <= 32'd0; rem_o <= 16'd0;
        end else begin
            done <= 1'b0;
            unique case (st)
                D_IDLE: if (start) begin
                    if (dvs == 16'd0) begin
                        // RISC-V DIV/REM by zero: q = all ones, r = dividend
                        quo   <= 32'hFFFFFFFF;
                        rem_o <= dvd[15:0];
                        done  <= 1'b1;
                    end else begin
                        q   <= 32'd0;
                        d   <= dvd;
                        r   <= 17'd0;
                        cnt <= 6'd0;
                        st  <= D_RUN;
                    end
                end
                D_RUN: begin
                    d <= d << 1;
                    if (sub_ok) begin
                        r <= rnext - {1'b0, dvs};
                        q <= {q[30:0], 1'b1};
                    end else begin
                        r <= rnext[16:0];
                        q <= {q[30:0], 1'b0};
                    end
                    cnt <= cnt + 6'd1;
                    if (cnt == 6'd31) st <= D_DONE;
                end
                D_DONE: begin
                    done   <= 1'b1;
                    quo    <= q;
                    rem_o  <= r[15:0];
                    st     <= D_IDLE;
                end
            endcase
        end
    end
endmodule
