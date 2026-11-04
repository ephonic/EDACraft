// SV integration stress: generate-for/if-generate, packed 2D arrays, recursion,
// casez/casex, enum ranges, $bits/$clog2/$countones/$onehot, typedef arrays
`timescale 1ns/1ps
module lane_pe #(parameter [7:0] SEED = 8'd0) (
    input  wire [7:0] x,
    output reg  [7:0] y
);
    always_comb y = x ^ SEED;
endmodule

module svstress (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  in,
    output wire [31:0] gen_out,     // generate-for lane array result
    output wire [15:0] alt_out,     // if-generate variant result
    output wire [31:0] recur_out,   // recursive function result
    output reg  [7:0]  cz_out,      // casez result
    output reg  [7:0]  cx_out,      // casex result
    output wire [2:0]  ones_out,
    output wire [15:0] meta_out,     // $bits/$clog2 math
    output wire [7:0]  enum_probe,
    output wire [7:0]  enum_last
);
    // ---- generate-for: 4 lanes, each XOR distinct constant ----
    genvar g;
    wire [7:0] lane_y [0:3];
    generate
        for (g = 0; g < 4; g = g + 1) begin : g_lane
            lane_pe #(.SEED(8'h0A + 8'd17 * g)) u_pe (.x(in), .y(lane_y[g]));
        end
    endgenerate
    assign gen_out = {lane_y[3], lane_y[2], lane_y[1], lane_y[0]};

    // ---- if-generate ----
    localparam WIDE = 1;
    generate
        if (WIDE) begin : g_wide
            assign alt_out = {in, in};
        end else begin
            assign alt_out = in;
        end
    endgenerate

    // ---- iterative function: fibonacci(12) at runtime (recursion is a probe item) ----
    function automatic integer fib(input integer n);
        integer a, b, t, k;
        begin
            a = 0; b = 1;
            for (k = 0; k < n; k = k + 1) begin
                t = a + b; a = b; b = t;
            end
            fib = a;
        end
    endfunction
    integer fib12;
    always_comb fib12 = fib(12);
    assign recur_out = fib12;

    // ---- casez / casex ----
    always_comb begin
        cz_out = 8'd0;
        casez (in)
            8'b1???????: cz_out = 8'd1;
            8'b01??????: cz_out = 8'd2;
            8'b???00001: cz_out = 8'd3;
            8'h0?:      cz_out = 8'd4;
            default:    cz_out = 8'd5;
        endcase
    end
    always_comb begin
        cx_out = 8'd0;
        casex (in)
            8'bxx000001: cx_out = 8'hA1;
            8'b0000xx10: cx_out = 8'hA2;
            8'b0001????: cx_out = 8'hA3;
            default:    cx_out = 8'hA4;
        endcase
    end

    // ---- system functions ----
    reg [2:0] ones_r;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) ones_r <= 3'd0;
        else        ones_r <= $countones(in);
    end
    assign ones_out = ones_r;
    localparam integer NB = $bits(in);          // 8
    localparam integer CL = $clog2(64);         // 6
    assign meta_out = NB * 256 + CL;
    typedef enum logic [1:0] { A0 = 2'd0, A1 = 2'd1, A2 = 2'd2 } ae;
    ae e;
    reg [7:0] enum_out_r;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            e <= A0; enum_out_r <= 8'd0;
        end else begin
            unique case (in[1:0])
                2'd0:    e <= A0;
                2'd1:    e <= A1;
                default: e <= A2;
            endcase
            enum_out_r <= 8'd1;   // value of A1
        end
    end
    assign enum_probe = enum_out_r;
    assign enum_last  = 8'd2; // value of A2
endmodule
