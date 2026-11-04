// SystemVerilog features integration test (dsim-0.13.0 supported subset):
// enum (+.next/.prev), packed struct (incl. cross-module), always_ff/always_comb,
// unique case, $countones, immediate assertion
`timescale 1ns/1ps
module sv_features (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        go,
    input  wire [7:0]  in_a,
    output reg  [16:0] packed_out,
    output wire [1:0]  state_o,
    output reg         done_o,
    output wire [7:0]  ones_cnt_o
);
    typedef enum logic [1:0] { IDLE = 2'd0, RUN = 2'd1, DONE = 2'd2, ERR = 2'd3 } state_e;
    typedef struct packed {
        logic [7:0] addr;
        logic [7:0] data;
        logic       wr;
    } req_t;

    state_e st, st_nxt;
    req_t   req;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st     <= IDLE;
            done_o <= 1'b0;
            req.addr <= 8'h0; req.data <= 8'h0; req.wr <= 1'b0;
        end else begin
            st <= st_nxt;
            done_o <= (st_nxt == DONE);
            if (go && st == IDLE) begin
                req.addr <= in_a;
                req.data <= in_a ^ 8'h5A;
                req.wr   <= in_a[0];
            end
        end
    end

    always_comb begin
        st_nxt = st;
        unique case (st)
            IDLE: if (go) st_nxt = RUN;
            RUN:  st_nxt = DONE;
            DONE: st_nxt = IDLE;
            ERR:  st_nxt = IDLE;
        endcase
    end

    always_comb packed_out = {req.addr, req.data, req.wr};

    assign state_o = st;

    // $countones probe
    reg [7:0] ones_cnt;
    assign ones_cnt_o = ones_cnt;
    always_ff @(posedge clk) ones_cnt <= $countones(in_a);

    // immediate assertion probe
    reg err_seen;
    always_ff @(posedge clk)
        if (st == ERR) begin
            assert (go == 1'b0) else err_seen = 1'b1;
        end
endmodule
