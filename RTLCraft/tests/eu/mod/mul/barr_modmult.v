module barr_modmult #(parameter DATA_WIDTH = 256, E_WIDTH = 2, VALID_WIDTH = 1 )
    (   
        clk,
        rst_n,
        mul_a,
        mul_b,
        pre_c,
        prime,
        en,
        i_valid,
        o_valid,
        res
    );

    input clk;
    input rst_n;
    input en;
    input [VALID_WIDTH-1:0] i_valid;
    input [DATA_WIDTH-1:0] mul_a;
    input [DATA_WIDTH-1:0] mul_b;
    input [DATA_WIDTH  :0] pre_c;
    input [DATA_WIDTH-1:0] prime;

    output [VALID_WIDTH-1:0] o_valid;
    output [DATA_WIDTH-1:0] res;
    localparam F_WIDTH   = DATA_WIDTH * 2;
    localparam M_SHIFT= 5;
    localparam F_SHIFT= M_SHIFT * 2-1;
    localparam V_SHIFT= M_SHIFT * 3+2;
    //------------------------------------Coarse Approximation------------------------------------//
    //////////////////////////////////////Full Integer Multiplier///////////////////////////////////
    wire [F_WIDTH-1:0] full_mul_res;

    js_zk_mul_level3 #(DATA_WIDTH,DATA_WIDTH,F_WIDTH) u_full_mul
    (
        .clk(clk),
        .rstn(rst_n),
        .a(mul_a),
        .b(mul_b),
        .en0(en),
        .en1(en),
        .en2(en),
        .en3(en),
        .en4(en),
        .res(full_mul_res)
    );

    //////////////////////////Four Level Recursive Approximate Msb Multiplier////////////////////////
    wire [DATA_WIDTH-1:0] approx_a;
    reg  [DATA_WIDTH  :0] approx_b;
    wire [DATA_WIDTH-1:0] approx_res;
    assign approx_a = full_mul_res[F_WIDTH-1:DATA_WIDTH];
    always @(posedge clk)
    if(en)
        approx_b <= pre_c;
    
    approx_msb_mul_level3 #(DATA_WIDTH) u_approx_msb_mul
    (
        .clk(clk),
        .rst_n(rst_n),
        .a(approx_a),
        .b(approx_b),
        .en0(en),
        .en1(en),
        .en2(en),
        .en3(en),
        .en4(en),
        .res(approx_res)
    );

    /////////////////////////////Four Level Recursive Lsb Multiplier/////////////////////////////////
    wire        [DATA_WIDTH-1        :0] lsb_mul_a;
    wire        [DATA_WIDTH-1        :0] lsb_mul_b;
    wire        [DATA_WIDTH+E_WIDTH-1:0] lsb_mul_res;
    wire        [DATA_WIDTH+E_WIDTH-1:0] r_alpha;
    wire signed [DATA_WIDTH+E_WIDTH  :0] r_alpha_tmp;
    reg         [DATA_WIDTH+E_WIDTH-1:0] full_mul_res_arr [F_SHIFT:0];

    always @ (posedge clk or negedge rst_n) begin
        if(!rst_n)begin
            full_mul_res_arr[0] <= 0;
        end
        else if (en) begin
            full_mul_res_arr[0] <= full_mul_res[DATA_WIDTH+E_WIDTH-1:0];
        end
    end
    genvar shft;
    generate
        for(shft=0; shft<F_SHIFT; shft=shft+1) begin:FULL_MUL_RES_BLOCK
            always @ (posedge clk or negedge rst_n) begin
                if(!rst_n) begin
                    full_mul_res_arr[shft+1] <= 0;
                end
                else if(en) begin
                    full_mul_res_arr[shft+1] <= full_mul_res_arr[shft];
                end
            end
        end
    endgenerate

    reg [DATA_WIDTH-1:0] prime_t;
    always @(posedge clk)
    if(en)
       prime_t <= prime;

    assign lsb_mul_a = approx_res;
    assign lsb_mul_b = prime_t;
    lsb_half_mul_level3 #(DATA_WIDTH, DATA_WIDTH, E_WIDTH) u_lsb_mul
    (
        .clk(clk),
        .rst_n(rst_n),
        .a(lsb_mul_a),
        .b(lsb_mul_b),
        .en0(en),
        .en1(en),
        .en2(en),
        .en3(en),
        .en4(en),
        .res(lsb_mul_res)
    );
    assign r_alpha_tmp = full_mul_res_arr[F_SHIFT]-lsb_mul_res;
    assign r_alpha     = r_alpha_tmp[DATA_WIDTH+E_WIDTH] ? r_alpha_tmp + {1'b1,{(DATA_WIDTH+E_WIDTH){1'b0}}} : r_alpha_tmp[DATA_WIDTH+E_WIDTH-1:0];
    reg [DATA_WIDTH+E_WIDTH-1:0] r_alpha_t;

    always @(posedge clk)
    if(en)
       r_alpha_t <= r_alpha;


    //------------------------------------Fine Approximation------------------------------------//
    wire signed [DATA_WIDTH+E_WIDTH  :0] r_tmp1;
    wire        [DATA_WIDTH+E_WIDTH-1:0] r_tmp2;
    wire signed [DATA_WIDTH+E_WIDTH  :0] r_tmp3;
    wire        [DATA_WIDTH        -1:0] res_tmp;
    reg         [DATA_WIDTH        -1:0] res;
    assign r_tmp1  = r_alpha_t - {prime_t,1'b0};
    assign r_tmp2  = r_tmp1[DATA_WIDTH+E_WIDTH] ? r_alpha_t : r_tmp1[DATA_WIDTH+E_WIDTH-1:0];
    assign r_tmp3  = r_tmp2 - prime_t;
    assign res_tmp = r_tmp3[DATA_WIDTH+E_WIDTH] ? r_tmp2[DATA_WIDTH-1:0]  : r_tmp3[DATA_WIDTH-1:0];
    
    always @ (posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            res <= 0;
        end
        else if(en) begin
            res <= res_tmp;
        end
    end
    //------------------------------------Valid delay-----------------------------//
    reg  [VALID_WIDTH-1:0] valid_array [V_SHIFT:0];
    assign o_valid = valid_array[V_SHIFT];

    always@(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            valid_array[0]                                 <= 0;
        end
        else if(en)begin
            valid_array[0]                                 <= i_valid;
        end
    end
    
    genvar v_shft;
    generate
        for(v_shft=0; v_shft < V_SHIFT; v_shft=v_shft+1) begin: VALID_DELAY_BLOCK
            always @(posedge clk or negedge rst_n) begin
                if(!rst_n)
                    valid_array[v_shft+1]                    <= 0;	    
                else if(en)
                    valid_array[v_shft+1]                    <= valid_array[v_shft];
            end
        end
    endgenerate


endmodule
