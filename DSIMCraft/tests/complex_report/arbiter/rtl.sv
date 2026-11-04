// round-robin arbitrated SRAM writer: 4 client FIFOs (generate-for) + rotating arbiter
`timescale 1ns/1ps
module client_fifo #(
    parameter [3:0] DEPTH = 8
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        push,
    input  wire [7:0]  din,
    output wire        ready,   // not full
    input  wire        pop,
    output wire [7:0]  dout,
    output wire        valid    // not empty
);
    reg [7:0] mem [0:DEPTH-1];
    reg [2:0] wptr, rptr;
    reg [3:0] count;

    assign ready = (count != DEPTH);
    assign valid = (count != 4'd0);
    assign dout  = mem[rptr];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wptr <= 3'd0; rptr <= 3'd0; count <= 4'd0;
        end else begin
            unique case ({push && ready, pop && valid})
                2'b10: begin mem[wptr] <= din; wptr <= wptr + 3'd1; count <= count + 4'd1; end
                2'b01: begin                     rptr <= rptr + 3'd1; count <= count - 4'd1; end
                2'b11: begin mem[wptr] <= din; wptr <= wptr + 3'd1; rptr <= rptr + 3'd1; end
                default: ;
            endcase
        end
    end
endmodule

module rr_mux_sram (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [3:0]  c_valid,
    input  wire [31:0] c_data,     // {c3, c2, c1, c0} bytes
    output wire [3:0]  c_ready,
    output reg         mem_wr,
    output reg  [7:0]  mem_addr,
    output reg  [7:0]  mem_wdata,
    output reg  [1:0]  mem_sel,
    output reg  [1:0]  last_served,
    output reg  [3:0]  occ_nz      // registered: per-client non-empty (post-edge)
);
    wire [7:0] fifo_dout0, fifo_dout1, fifo_dout2, fifo_dout3;
    wire       nempty0, nempty1, nempty2, nempty3;
    wire [3:0] nempty = {nempty3, nempty2, nempty1, nempty0};
    wire       any = |nempty;

    // rotating priority: (last+1, last+2, last+3, last)
    wire [1:0] p0 = last_served + 2'd1;
    wire [1:0] p1 = last_served + 2'd2;
    wire [1:0] p2 = last_served + 2'd3;
    wire [1:0] p3 = last_served;
    wire [1:0] winner = nempty[p0] ? p0 :
                        nempty[p1] ? p1 :
                        nempty[p2] ? p2 :
                        nempty[p3] ? p3 : 2'd0;

    wire [3:0] pop_vec = {4{any}} & (4'b0001 << winner);

    wire [7:0] wdata_mux = (winner == 2'd0) ? fifo_dout0 :
                           (winner == 2'd1) ? fifo_dout1 :
                           (winner == 2'd2) ? fifo_dout2 : fifo_dout3;

    client_fifo #(.DEPTH(8)) u_f0 (
        .clk(clk), .rst_n(rst_n), .push(c_valid[0]), .din(c_data[7:0]),
        .ready(c_ready[0]), .pop(pop_vec[0]), .dout(fifo_dout0), .valid(nempty0));
    client_fifo #(.DEPTH(8)) u_f1 (
        .clk(clk), .rst_n(rst_n), .push(c_valid[1]), .din(c_data[15:8]),
        .ready(c_ready[1]), .pop(pop_vec[1]), .dout(fifo_dout1), .valid(nempty1));
    client_fifo #(.DEPTH(8)) u_f2 (
        .clk(clk), .rst_n(rst_n), .push(c_valid[2]), .din(c_data[23:16]),
        .ready(c_ready[2]), .pop(pop_vec[2]), .dout(fifo_dout2), .valid(nempty2));
    client_fifo #(.DEPTH(8)) u_f3 (
        .clk(clk), .rst_n(rst_n), .push(c_valid[3]), .din(c_data[31:24]),
        .ready(c_ready[3]), .pop(pop_vec[3]), .dout(fifo_dout3), .valid(nempty3));

    // per-client drain address counters
    reg [7:0] addr_cnt [0:3];
    reg [3:0] nz_r;
    integer k;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mem_wr <= 1'b0; mem_addr <= 8'd0; mem_wdata <= 8'd0;
            mem_sel <= 2'd0; last_served <= 2'd3; nz_r <= 4'd0;
            for (k = 0; k < 4; k = k + 1) addr_cnt[k] <= 8'd0;
        end else begin
            if (any) begin
                mem_wr    <= 1'b1;
                mem_sel   <= winner;
                mem_wdata <= wdata_mux;
                mem_addr  <= addr_cnt[winner];
                addr_cnt[winner] <= addr_cnt[winner] + 8'd1;
                last_served <= winner;
            end else begin
                mem_wr <= 1'b0;
            end
            nz_r <= nempty;
        end
    end
    assign occ_nz = nz_r;
endmodule
