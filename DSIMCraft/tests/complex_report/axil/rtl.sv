// AXI4-Lite slave: RW scratch regs, RO free-run counter, RW1C sticky flags, SLVERR unmapped
`timescale 1ns/1ps
module axil_slave (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        event_in,     // level; posedge latched into sticky[0]
    // AW
    input  wire [31:0] awaddr,
    input  wire [2:0]  awprot,
    input  wire        awvalid,
    output reg         awready,
    // W
    input  wire [31:0] wdata,
    input  wire [3:0]  wstrb,
    input  wire        wvalid,
    output reg         wready,
    // B
    output reg         bvalid,
    input  wire        bready,
    output reg  [1:0]  bresp,
    // AR
    input  wire [31:0] araddr,
    input  wire [2:0]  arprot,
    input  wire        arvalid,
    output reg         arready,
    // R
    output reg         rvalid,
    input  wire        rready,
    output reg  [31:0] rdata,
    output reg  [1:0]  rresp
);
    localparam logic [1:0] RESP_OKAY   = 2'b00;
    localparam logic [1:0] RESP_SLVERR = 2'b10;

    function automatic [31:0] lane_merge(input [31:0] d, input [31:0] old, input [3:0] s);
        lane_merge = {s[3] ? d[31:24] : old[31:24],
                      s[2] ? d[23:16] : old[23:16],
                      s[1] ? d[15:8]  : old[15:8],
                      s[0] ? d[7:0]   : old[7:0]};
    endfunction

    typedef enum logic [1:0] { W_IDLE, W_RESP } wst_e;
    typedef enum logic       { R_IDLE, R_DATA } rst_e;
    wst_e wst;
    rst_e rst;

    reg [31:0] scr0, scr1;   // 0x00 / 0x04 RW
    reg [31:0] cnt;          // 0x08 RO free-running when scr0[0]
    reg [1:0]  sticky;       // 0x0C RW1C
    reg        event_d;

    wire wr_accept = (wst == W_IDLE) && awvalid && wvalid; // awready/wready high in W_IDLE
    wire wr_mapped = (awaddr[31:4] == 28'd0);
    wire is_scr0   = wr_mapped && (awaddr[3:2] == 2'd0);
    wire is_scr1   = wr_mapped && (awaddr[3:2] == 2'd1);
    wire is_stk    = wr_mapped && (awaddr[3:2] == 2'd3);

    // write-side core
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wst <= W_IDLE; awready <= 1'b0; wready <= 1'b0;
            bvalid <= 1'b0; bresp <= RESP_OKAY;
            scr0 <= 32'd0; scr1 <= 32'd0;
            cnt <= 32'd0; sticky <= 2'b00; event_d <= 1'b0;
        end else begin
            event_d <= event_in;
            if (scr0[0]) cnt <= cnt + 32'd1;
            sticky <= sticky | {(cnt == 32'h0000_0080), (event_in & ~event_d)};

            unique case (wst)
                W_IDLE: begin
                    awready <= 1'b1; wready <= 1'b1;
                    if (awvalid && awready && wvalid && wready) begin
                        awready <= 1'b0; wready <= 1'b0;
                        wst <= W_RESP;
                        bvalid <= 1'b1;
                        bresp <= wr_mapped ? RESP_OKAY : RESP_SLVERR;
                        if (is_scr0) scr0 <= lane_merge(wdata, scr0, wstrb);
                        if (is_scr1) scr1 <= lane_merge(wdata, scr1, wstrb);
                        if (is_stk && wstrb[0]) sticky <= sticky & ~wdata[1:0]; // RW1C (last-assign wins)
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

    // read-side core
    reg [31:0] rdata_c;
    reg [1:0]  rresp_c;
    always_comb begin
        rdata_c = 32'd0; rresp_c = RESP_OKAY;
        if (araddr[31:4] == 28'd0) begin
            unique case (araddr[3:2])
                2'd0: rdata_c = scr0;
                2'd1: rdata_c = scr1;
                2'd2: rdata_c = cnt;
                2'd3: rdata_c = {30'd0, sticky};
            endcase
        end else begin
            rresp_c = RESP_SLVERR;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rst <= R_IDLE; arready <= 1'b0; rvalid <= 1'b0;
            rdata <= 32'd0; rresp <= RESP_OKAY;
        end else begin
            unique case (rst)
                R_IDLE: begin
                    arready <= 1'b1;
                    if (arvalid && arready) begin
                        arready <= 1'b0;
                        rvalid  <= 1'b1;
                        rdata   <= rdata_c;
                        rresp   <= rresp_c;
                        rst     <= R_DATA;
                    end
                end
                R_DATA: begin
                    if (rvalid && rready) begin
                        rvalid <= 1'b0;
                        rst <= R_IDLE;
                    end
                end
            endcase
        end
    end

    wire unused_ok = &{1'b1, awprot, arprot};
endmodule
