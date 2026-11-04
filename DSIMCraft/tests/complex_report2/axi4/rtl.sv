// full AXI4 burst slave: INCR/WRAP bursts, wstrb merge, wlast checks,
// per-ID read delay for out-of-order completion, FIXED -> SLVERR
`timescale 1ns/1ps
module axi4_slave #(
    parameter ID_W = 4,
    parameter [3:0] DELAY_ID = 4'd1,
    parameter [3:0] DELAY_CYCLES = 8
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire [31:0]      awaddr,
    input  wire [3:0]       awlen,
    input  wire [1:0]       awburst,
    input  wire [ID_W-1:0]  awid,
    input  wire             awvalid,
    output reg              awready,
    input  wire [31:0]      wdata,
    input  wire [3:0]       wstrb,
    input  wire             wlast,
    input  wire             wvalid,
    output reg              wready,
    output reg              bvalid,
    input  wire             bready,
    output reg  [1:0]       bresp,
    output reg  [ID_W-1:0]  bid,
    input  wire [31:0]      araddr,
    input  wire [3:0]       arlen,
    input  wire [1:0]       arburst,
    input  wire [ID_W-1:0]  arid,
    input  wire             arvalid,
    output reg              arready,
    output reg              rvalid,
    input  wire             rready,
    output reg  [31:0]      rdata,
    output reg  [1:0]       rresp,
    output reg  [ID_W-1:0]  rid,
    output reg              rlast
);
    localparam logic [1:0] B_FIXED = 2'b00, B_INCR = 2'b01, B_WRAP = 2'b10;
    localparam logic [1:0] RESP_OKAY = 2'b00, RESP_SLVERR = 2'b10;

    reg [31:0] mem [0:255];
    integer i;
    function automatic [31:0] pat(input [7:0] a);
        pat = {a, ~a, (a ^ 8'h5A), (a + 8'hA5)};
    endfunction

    function automatic [31:0] lane_merge(input [31:0] d, input [31:0] old, input [3:0] s);
        lane_merge = {s[3] ? d[31:24] : old[31:24],
                      s[2] ? d[23:16] : old[23:16],
                      s[1] ? d[15:8]  : old[15:8],
                      s[0] ? d[7:0]   : old[7:0]};
    endfunction

    // word-level next address in burst; WRAP window = (len+1) words, mask = len
    function automatic [7:0] wnext(input [7:0] a, input [1:0] burst, input [3:0] len);
        if (burst == B_WRAP) wnext = (a & ~len) | ((a + 8'd1) & len);
        else                 wnext = a + 8'd1;
    endfunction

    // ---------------- write path ----------------
    typedef enum logic [1:0] { W_IDLE, W_BEATS, W_RESP } wst_e;
    wst_e wst;
    reg [7:0]  wa_waddr;      // current word address
    reg [3:0]  wa_len, wb_cnt;
    reg [1:0]  wa_burst;
    reg [ID_W-1:0] wa_id;
    reg        w_err;

    wire [7:0] wa_next = wnext(wa_waddr, wa_burst, wa_len);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 256; i = i + 1) mem[i] <= pat(i[7:0]);
            wst <= W_IDLE; awready <= 1'b0; wready <= 1'b0;
            bvalid <= 1'b0; bresp <= RESP_OKAY; bid <= '0;
            wa_waddr <= 8'd0; wa_len <= 4'd0; wa_burst <= B_INCR; wa_id <= '0;
            wb_cnt <= 4'd0; w_err <= 1'b0;
        end else begin
            unique case (wst)
                W_IDLE: begin
                    awready <= 1'b1; wready <= 1'b1;
                    if (awvalid && awready && wvalid && wready) begin
                        awready <= 1'b0; wready <= 1'b0;
                        wa_waddr <= awaddr[9:2];
                        wa_len   <= awlen;
                        wa_burst <= awburst;
                        wa_id    <= awid;
                        wb_cnt   <= 4'd0;
                        w_err    <= (awburst == B_FIXED);
                        if (awburst != B_FIXED)
                            mem[awaddr[9:2]] <= lane_merge(wdata, mem[awaddr[9:2]], wstrb);
                        if (wlast) begin
                            // single beat: legal only when len == 0
                            bid    <= awid;
                            bresp  <= (w_err || awlen != 4'd0) ? RESP_SLVERR : RESP_OKAY;
                            bvalid <= 1'b1;
                            wst    <= W_RESP;
                        end else begin
                            wst <= W_BEATS;
                        end
                    end
                end
                W_BEATS: begin
                    wready <= 1'b1;    // continue accepting beats
                    if (wvalid && wready) begin
                        if (wa_burst != B_FIXED)
                            mem[wa_next] <= lane_merge(wdata, mem[wa_next], wstrb);
                        wa_waddr <= wa_next;
                        wb_cnt   <= wb_cnt + 4'd1;
                        if (wlast) begin
                            wready  <= 1'b0;
                            bid    <= wa_id;
                            bresp  <= (w_err || (wb_cnt + 4'd1 != wa_len)) ? RESP_SLVERR : RESP_OKAY;
                            bvalid <= 1'b1;
                            wst    <= W_RESP;
                        end
                    end
                end
                W_RESP: begin
                    if (bvalid && bready) begin
                        bvalid <= 1'b0;
                        wst <= W_IDLE;
                    end
                end
            endcase
        end
    end

    // ---------------- read path: 2-entry AR queue, non-delayed reads overtake delayed ----------------
    typedef enum logic [1:0] { R_IDLE, R_WAIT, R_BEATS } rst_e;
    rst_e rst;
    reg [31:0] pq_addr [0:1];
    reg [3:0]  pq_len  [0:1];
    reg [1:0]  pq_burst[0:1];
    reg [ID_W-1:0] pq_id[0:1];
    reg [1:0]  pq_v;
    reg [7:0]  ra_waddr;
    reg [3:0]  ra_len, rb_cnt, rd_cnt;
    reg [1:0]  ra_burst;
    reg [ID_W-1:0] ra_id;

    wire [7:0] ra_next = wnext(ra_waddr, ra_burst, ra_len);

    wire pick0 = pq_v[0] && (pq_id[0] != DELAY_ID);
    wire pick1 = pq_v[1] && (pq_id[1] != DELAY_ID);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rst <= R_IDLE; arready <= 1'b1; rvalid <= 1'b0; rlast <= 1'b0;
            rdata <= 32'd0; rresp <= RESP_OKAY; rid <= '0;
            ra_waddr <= 8'd0; ra_len <= 4'd0; ra_burst <= B_INCR; ra_id <= '0;
            rb_cnt <= 4'd0; rd_cnt <= 4'd0;
            pq_v <= 2'b00; pq_addr[0] <= 32'd0; pq_addr[1] <= 32'd0;
            pq_len[0] <= 4'd0; pq_len[1] <= 4'd0;
            pq_burst[0] <= B_INCR; pq_burst[1] <= B_INCR;
            pq_id[0] <= '0; pq_id[1] <= '0;
        end else begin
            unique case (rst)
                R_IDLE: begin
                    arready <= 1'b1;
                    if (arvalid && arready) begin
                        if (!pq_v[0]) begin
                            pq_addr[0] <= araddr; pq_len[0] <= arlen;
                            pq_burst[0] <= arburst; pq_id[0] <= arid; pq_v[0] <= 1'b1;
                        end else if (!pq_v[1]) begin
                            pq_addr[1] <= araddr; pq_len[1] <= arlen;
                            pq_burst[1] <= arburst; pq_id[1] <= arid; pq_v[1] <= 1'b1;
                        end
                    end
                    // start next burst: non-delayed overtakes delayed
                    if (pick0 || pick1 || (|pq_v)) begin
                        if (pick0) begin
                            ra_waddr <= pq_addr[0][9:2]; ra_len <= pq_len[0];
                            ra_burst <= pq_burst[0]; ra_id <= pq_id[0];
                            pq_v[0] <= 1'b0; rb_cnt <= 4'd0;
                            if (pq_burst[0] == B_FIXED) begin
                                rresp <= RESP_SLVERR; rdata <= 32'd0;
                                rid <= pq_id[0]; rvalid <= 1'b1; rlast <= 1'b1;
                                rst <= R_BEATS;
                            end else if (pq_id[0] == DELAY_ID) begin
                                rd_cnt <= DELAY_CYCLES; rst <= R_WAIT;
                            end else begin
                                rdata  <= mem[pq_addr[0][9:2]];
                                rresp  <= RESP_OKAY; rid <= pq_id[0];
                                rvalid <= 1'b1; rlast <= (pq_len[0] == 4'd0);
                                rst <= R_BEATS;
                            end
                        end else if (pick1) begin
                            ra_waddr <= pq_addr[1][9:2]; ra_len <= pq_len[1];
                            ra_burst <= pq_burst[1]; ra_id <= pq_id[1];
                            pq_v[1] <= 1'b0; rb_cnt <= 4'd0;
                            if (pq_burst[1] == B_FIXED) begin
                                rresp <= RESP_SLVERR; rdata <= 32'd0;
                                rid <= pq_id[1]; rvalid <= 1'b1; rlast <= 1'b1;
                                rst <= R_BEATS;
                            end else if (pq_id[1] == DELAY_ID) begin
                                rd_cnt <= DELAY_CYCLES; rst <= R_WAIT;
                            end else begin
                                rdata  <= mem[pq_addr[1][9:2]];
                                rresp  <= RESP_OKAY; rid <= pq_id[1];
                                rvalid <= 1'b1; rlast <= (pq_len[1] == 4'd0);
                                rst <= R_BEATS;
                            end
                        end else if (pq_v[0]) begin
                            // only delayed entry [0] present
                            ra_waddr <= pq_addr[0][9:2]; ra_len <= pq_len[0];
                            ra_burst <= pq_burst[0]; ra_id <= pq_id[0];
                            pq_v[0] <= 1'b0; rb_cnt <= 4'd0;
                            rd_cnt <= DELAY_CYCLES; rst <= R_WAIT;
                        end else if (pq_v[1]) begin
                            ra_waddr <= pq_addr[1][9:2]; ra_len <= pq_len[1];
                            ra_burst <= pq_burst[1]; ra_id <= pq_id[1];
                            pq_v[1] <= 1'b0; rb_cnt <= 4'd0;
                            rd_cnt <= DELAY_CYCLES; rst <= R_WAIT;
                        end
                    end
                end
                R_WAIT: begin
                    arready <= 1'b1;                      // keep accepting new ARs
                    if (arvalid && arready)
                    if (arvalid && arready) begin
                        if (!pq_v[0]) begin
                            pq_addr[0] <= araddr; pq_len[0] <= arlen;
                            pq_burst[0] <= arburst; pq_id[0] <= arid; pq_v[0] <= 1'b1;
                        end else if (!pq_v[1]) begin
                            pq_addr[1] <= araddr; pq_len[1] <= arlen;
                            pq_burst[1] <= arburst; pq_id[1] <= arid; pq_v[1] <= 1'b1;
                        end
                    end
                    if (rd_cnt != 4'd0) rd_cnt <= rd_cnt - 4'd1;
                    else begin
                        rdata  <= mem[ra_waddr];
                        rresp  <= RESP_OKAY;
                        rid    <= ra_id;
                        rvalid <= 1'b1;
                        rlast  <= (ra_len == 4'd0);
                        rst    <= R_BEATS;
                    end
                end
                R_BEATS: begin
                    if (rvalid && rready) begin
                        if (rlast) begin
                            rvalid <= 1'b0;
                            rst <= R_IDLE;
                        end else begin
                            rb_cnt   <= rb_cnt + 4'd1;
                            ra_waddr <= ra_next;
                            rdata    <= mem[ra_next];
                            rlast    <= (rb_cnt + 4'd1 == ra_len);
                        end
                    end
                end
            endcase
        end
    end
endmodule
