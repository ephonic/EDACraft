// 2-way set-associative write-back cache: LRU, miss fill + dirty evict, flush op
`timescale 1ns/1ps
module cache2way #(
    parameter SETS = 16,        // sets
    parameter WPL  = 4          // words/line
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         req,
    input  wire         we,
    input  wire [31:0]  addr,
    input  wire [31:0]  wdata,
    output wire         ready,
    output reg          rvalid,
    output reg  [31:0]  rdata,
    input  wire         flush_req,
    output reg          flush_done,
    output reg          mreq,
    output reg          mwe,
    output reg  [31:0]  maddr,
    output reg  [127:0] mwdata,
    input  wire         mready,
    input  wire [1:0]   mstat,      // 00 idle, 01 rdata, 10 done
    input  wire [127:0] mrdata,
    output reg  [15:0]  hits,
    output reg  [15:0]  misses
);
    localparam IW = 4;   // log2(16)
    localparam OW = 2;   // log2(4)
    localparam [3:0] SETS_L = SETS;

    reg [23:0] tag_arr [0:2*SETS-1];     // tag = addr[31:8]
    reg [31:0] dat_arr [0:2*SETS*WPL-1];
    reg        v_arr   [0:2*SETS-1];
    reg        d_arr   [0:2*SETS-1];
    reg        lru     [0:SETS-1];       // 1: way1 recently used; 0: way0 recently used

    function automatic integer lin(input integer way, input integer set);
        lin = way * SETS + set;
    endfunction
    function automatic integer dlin(input integer way, input integer set, input integer off);
        dlin = (way * SETS + set) * WPL + off;
    endfunction

    typedef enum logic [2:0] { S_RDY, S_EJECT_WB, S_FILL_CMD, S_FILL_WAIT,
                               S_RESP, S_FLUSH_NEXT, S_FLUSH_WB, S_FLUSH_DONE } st_e;
    st_e st;

    assign ready = (st == S_RDY);

    reg        op_we;
    reg [23:0] op_tag;
    reg [3:0]  op_idx;
    reg [1:0]  op_off;
    reg [31:0] op_wdata;
    reg        op_hit;
    reg        op_way;

    wire [23:0] a_tag = addr[31:8];
    wire [3:0]  a_idx = addr[7:4];
    wire [1:0]  a_off = addr[3:2];

    // always_comb: content-sensitive on unpacked arrays (continuous assigns are not,
    // per LRM — and VCS honors that literally, causing stale hit/miss evaluation)
    reg h0, h1, victim;
    always_comb begin
        h0 = v_arr[lin(0, a_idx)] && (tag_arr[lin(0, a_idx)] == a_tag);
        h1 = v_arr[lin(1, a_idx)] && (tag_arr[lin(1, a_idx)] == a_tag);
        victim = ~lru[a_idx];     // evict the not-recently-used way
    end

    integer w, s, o;
    reg [4:0] scan;
    reg       f_w0;   // way0 of current set already flushed

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_RDY; rvalid <= 1'b0; rdata <= 32'd0;
            mreq <= 1'b0; mwe <= 1'b0; maddr <= 32'd0; mwdata <= 128'd0;
            flush_done <= 1'b0; scan <= 5'd0; f_w0 <= 1'b0;
            hits <= 16'd0; misses <= 16'd0;
            for (w = 0; w < 2; w = w + 1)
                for (s = 0; s < SETS; s = s + 1) begin
                    v_arr[lin(w, s)] <= 1'b0;
                    d_arr[lin(w, s)] <= 1'b0;
                    lru[s] <= 1'b0;
                end
        end else begin
            rvalid <= 1'b0;
            flush_done <= 1'b0;
            unique case (st)
                S_RDY: begin
                    if (req && ready) begin
                        op_we    <= we;
                        op_tag   <= a_tag;
                        op_idx   <= a_idx;
                        op_off   <= a_off;
                        op_wdata <= wdata;
                        op_hit   <= h0 || h1;
                        if (h0) begin op_way <= 1'b0; hits <= hits + 16'd1; end
                        else if (h1) begin op_way <= 1'b1; hits <= hits + 16'd1; end
                        else begin
                            misses <= misses + 16'd1;
                            op_way <= victim;
                        end
                        if (h0 || h1) st <= S_RESP;
                        else if (v_arr[lin(victim, a_idx)] && d_arr[lin(victim, a_idx)])
                            st <= S_EJECT_WB;
                        else
                            st <= S_FILL_CMD;
                    end else if (flush_req) begin
                        scan <= 5'd0;
                        st <= S_FLUSH_NEXT;
                    end
                end
                S_EJECT_WB: begin
                    mreq   <= 1'b1;
                    mwe    <= 1'b1;
                    maddr  <= {tag_arr[lin(op_way, op_idx)], op_idx, 4'b0000};
                    mwdata <= {dat_arr[dlin(op_way, op_idx, 3)], dat_arr[dlin(op_way, op_idx, 2)],
                               dat_arr[dlin(op_way, op_idx, 1)], dat_arr[dlin(op_way, op_idx, 0)]};
                    if (mreq && mready) begin
                        mreq <= 1'b0;
                        st <= S_FILL_CMD;
                    end
                end
                S_FILL_CMD: begin
                    mreq  <= 1'b1;
                    mwe   <= 1'b0;
                    maddr <= {op_tag, op_idx, 4'b0000};
                    if (mreq && mready) begin
                        mreq <= 1'b0;
                        st <= S_FILL_WAIT;
                    end
                end
                S_FILL_WAIT: begin
                    if (mstat == 2'b10) begin
                        dat_arr[dlin(op_way, op_idx, 0)] <= mrdata[31:0];
                        dat_arr[dlin(op_way, op_idx, 1)] <= mrdata[63:32];
                        dat_arr[dlin(op_way, op_idx, 2)] <= mrdata[95:64];
                        dat_arr[dlin(op_way, op_idx, 3)] <= mrdata[127:96];
                        tag_arr[lin(op_way, op_idx)] <= op_tag;
                        v_arr[lin(op_way, op_idx)]   <= 1'b1;
                        d_arr[lin(op_way, op_idx)]   <= 1'b0;
                        st <= S_RESP;
                    end
                end
                S_RESP: begin
                    rvalid <= 1'b1;
                    lru[op_idx] <= op_way;
                    if (op_we) begin
                        dat_arr[dlin(op_way, op_idx, op_off)] <= op_wdata;
                        d_arr[lin(op_way, op_idx)] <= 1'b1;
                    end else begin
                        rdata <= dat_arr[dlin(op_way, op_idx, op_off)];
                    end
                    st <= S_RDY;
                end
                S_FLUSH_NEXT: begin
                    if (scan == 5'd16) begin
                        st <= S_FLUSH_DONE;
                    end else if (!f_w0 && v_arr[lin(0, scan)] && d_arr[lin(0, scan)]) begin
                        op_way <= 1'b0; op_idx <= scan[3:0]; f_w0 <= 1'b1;
                        st <= S_FLUSH_WB;
                    end else if (v_arr[lin(1, scan)] && d_arr[lin(1, scan)]) begin
                        op_way <= 1'b1; op_idx <= scan[3:0];
                        st <= S_FLUSH_WB;
                    end else begin
                        scan <= scan + 5'd1;
                        f_w0 <= 1'b0;
                    end
                end
                S_FLUSH_WB: begin
                    mreq  <= 1'b1;
                    mwe   <= 1'b1;
                    maddr <= {tag_arr[lin(op_way, op_idx)], op_idx, 4'b0000};
                    mwdata <= {dat_arr[dlin(op_way, op_idx, 3)], dat_arr[dlin(op_way, op_idx, 2)],
                               dat_arr[dlin(op_way, op_idx, 1)], dat_arr[dlin(op_way, op_idx, 0)]};
                    if (mreq && mready) begin
                        mreq <= 1'b0;
                        d_arr[lin(op_way, op_idx)] <= 1'b0;
                        st <= S_FLUSH_NEXT;   // rescan same set for the other way
                    end
                end
                S_FLUSH_DONE: begin
                    flush_done <= 1'b1;
                    if (!flush_req) st <= S_RDY;
                end
            endcase
        end
    end
endmodule
