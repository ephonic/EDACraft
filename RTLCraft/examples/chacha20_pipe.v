module chacha20rng_quarterround (
    input [31:0] ai,
    input [31:0] bi,
    input [31:0] ci,
    input [31:0] di,
    output [31:0] a,
    output [31:0] b,
    output [31:0] c,
    output [31:0] d
);

    logic [31:0] step1;
    logic [31:0] step2;
    logic [31:0] step3;
    logic [31:0] step4;
    logic [31:0] step5;
    logic [31:0] step6;
    logic [31:0] step7;
    logic [31:0] step8;
    logic [31:0] step9;
    logic [31:0] step10;
    logic [31:0] step11;
    logic [31:0] step12;

    assign step1 = (ai + bi);
    assign step2 = (di ^ step1);
    assign step3 = {step2[15:0], step2[31:16]};
    assign step4 = (ci + step3);
    assign step5 = (bi ^ step4);
    assign step6 = {step5[19:0], step5[31:20]};
    assign step7 = (step1 + step6);
    assign step8 = (step3 ^ step7);
    assign step9 = {step8[23:0], step8[31:24]};
    assign step10 = (step9 + step4);
    assign step11 = (step10 ^ step6);
    assign step12 = {step11[24:0], step11[31:25]};
    assign a = step7;
    assign b = step12;
    assign c = step10;
    assign d = step9;

endmodule

module chacha20rng_round (
    input clk,
    input rst_n,
    input i_valid,
    input [511:0] xin,
    input o_ready,
    input [511:0] init_state_in,
    output i_ready,
    output [511:0] xout,
    output reg o_valid,
    output reg [511:0] init_state_out
);

    reg stage1_valid;
    reg [511:0] init_state_stage1;
    reg [511:0] xout_t;
    logic [31:0] x [0:15];
    logic [31:0] t_out [0:15];
    reg [31:0] t_out_reg [0:15];
    logic [31:0] xd [0:15];
    logic [31:0] xo [0:15];

    generate
        genvar idx;
        for (idx = 0; idx < 16; idx = idx + 1) begin : genblk
            xd[idx] = t_out_reg[idx];
        end
    endgenerate
    generate
        genvar idx;
        for (idx = 0; idx < 4; idx = idx + 1) begin : genblk
            chacha20rng_quarterround u_qr (
                .ai(x[idx]),
                .bi(x[(idx + 4)]),
                .ci(x[(idx + 8)]),
                .di(x[(idx + 12)]),
                .a(t_out[idx]),
                .b(t_out[(idx + 4)]),
                .c(t_out[(idx + 8)]),
                .d(t_out[(idx + 12)])
            );

        end
    endgenerate
    chacha20rng_quarterround u_qr_5 (
        .ai(xd[0]),
        .bi(xd[5]),
        .ci(xd[10]),
        .di(xd[15]),
        .a(xo[0]),
        .b(xo[5]),
        .c(xo[10]),
        .d(xo[15])
    );

    chacha20rng_quarterround u_qr_6 (
        .ai(xd[1]),
        .bi(xd[6]),
        .ci(xd[11]),
        .di(xd[12]),
        .a(xo[1]),
        .b(xo[6]),
        .c(xo[11]),
        .d(xo[12])
    );

    chacha20rng_quarterround u_qr_7 (
        .ai(xd[2]),
        .bi(xd[7]),
        .ci(xd[8]),
        .di(xd[13]),
        .a(xo[2]),
        .b(xo[7]),
        .c(xo[8]),
        .d(xo[13])
    );

    chacha20rng_quarterround u_qr_8 (
        .ai(xd[3]),
        .bi(xd[4]),
        .ci(xd[9]),
        .di(xd[14]),
        .a(xo[3]),
        .b(xo[4]),
        .c(xo[9]),
        .d(xo[14])
    );

    assign x[0] = xin[31:0];
    assign x[1] = xin[63:32];
    assign x[2] = xin[95:64];
    assign x[3] = xin[127:96];
    assign x[4] = xin[159:128];
    assign x[5] = xin[191:160];
    assign x[6] = xin[223:192];
    assign x[7] = xin[255:224];
    assign x[8] = xin[287:256];
    assign x[9] = xin[319:288];
    assign x[10] = xin[351:320];
    assign x[11] = xin[383:352];
    assign x[12] = xin[415:384];
    assign x[13] = xin[447:416];
    assign x[14] = xin[479:448];
    assign x[15] = xin[511:480];

    assign i_ready = o_ready;
    assign xout = xout_t;

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            t_out_reg[0] <= 0;
            t_out_reg[1] <= 0;
            t_out_reg[2] <= 0;
            t_out_reg[3] <= 0;
            t_out_reg[4] <= 0;
            t_out_reg[5] <= 0;
            t_out_reg[6] <= 0;
            t_out_reg[7] <= 0;
            t_out_reg[8] <= 0;
            t_out_reg[9] <= 0;
            t_out_reg[10] <= 0;
            t_out_reg[11] <= 0;
            t_out_reg[12] <= 0;
            t_out_reg[13] <= 0;
            t_out_reg[14] <= 0;
            t_out_reg[15] <= 0;
            init_state_stage1 <= 0;
        end else begin
            if ((i_valid & i_ready)) begin
                t_out_reg[0] <= t_out[0];
                t_out_reg[1] <= t_out[1];
                t_out_reg[2] <= t_out[2];
                t_out_reg[3] <= t_out[3];
                t_out_reg[4] <= t_out[4];
                t_out_reg[5] <= t_out[5];
                t_out_reg[6] <= t_out[6];
                t_out_reg[7] <= t_out[7];
                t_out_reg[8] <= t_out[8];
                t_out_reg[9] <= t_out[9];
                t_out_reg[10] <= t_out[10];
                t_out_reg[11] <= t_out[11];
                t_out_reg[12] <= t_out[12];
                t_out_reg[13] <= t_out[13];
                t_out_reg[14] <= t_out[14];
                t_out_reg[15] <= t_out[15];
                init_state_stage1 <= init_state_in;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            xout_t <= 0;
            init_state_out <= 0;
        end else begin
            if ((stage1_valid & o_ready)) begin
                xout_t <= {xo[15], xo[14], xo[13], xo[12], xo[11], xo[10], xo[9], xo[8], xo[7], xo[6], xo[5], xo[4], xo[3], xo[2], xo[1], xo[0]};
                init_state_out <= init_state_stage1;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            stage1_valid <= 0;
        end else begin
            if (o_ready) begin
                stage1_valid <= i_valid;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            o_valid <= 0;
        end else begin
            if (o_ready) begin
                o_valid <= stage1_valid;
            end
        end
    end

endmodule

module u_core (
    input clk,
    input rst_n,
    input [255:0] seed,
    input [63:0] stream_id,
    input [63:0] counter,
    input i_valid,
    input o_ready,
    output i_ready,
    output [511:0] state,
    output o_valid
);

    logic [511:0] init_state;
    logic init_valid;
    logic [511:0] final_xout;
    logic [511:0] final_init;
    logic final_valid;
    logic [511:0] final_state;
    reg [511:0] state_reg;
    reg o_valid_reg;
    logic [511:0] xin [0:20];
    logic [511:0] xout [0:19];
    logic stage_valid [0:20];
    logic stage_ready [0:20];
    logic [511:0] init_state_stage [0:20];

    generate
        genvar i;
        for (i = 0; i < 20; i = i + 1) begin : genblk
            chacha20rng_round inst (
                .clk(clk),
                .rst_n(rst_n),
                .i_valid(stage_valid[i]),
                .i_ready(stage_ready[i]),
                .xin(xin[i]),
                .xout(xout[i]),
                .o_valid(stage_valid[(i + 1)]),
                .o_ready(stage_ready[(i + 1)]),
                .init_state_in(init_state_stage[i]),
                .init_state_out(init_state_stage[(i + 1)])
            );

            xin[(i + 1)] = xout[i];
        end
    endgenerate
    assign init_state = {stream_id[63:32], stream_id[31:0], counter[63:32], counter[31:0], seed[255:224], seed[223:192], seed[191:160], seed[159:128], seed[127:96], seed[95:64], seed[63:32], seed[31:0], 1797285236, 2036477234, 857760878, 1634760805};
    assign init_valid = i_valid;

    assign xin[0] = init_state;
    assign stage_valid[0] = i_valid;
    assign init_state_stage[0] = init_state;

    assign final_xout = xout[19];
    assign final_init = init_state_stage[20];
    assign final_valid = stage_valid[20];

    assign final_state = {(final_xout[511:480] + final_init[511:480]), (final_xout[479:448] + final_init[479:448]), (final_xout[447:416] + final_init[447:416]), (final_xout[415:384] + final_init[415:384]), (final_xout[383:352] + final_init[383:352]), (final_xout[351:320] + final_init[351:320]), (final_xout[319:288] + final_init[319:288]), (final_xout[287:256] + final_init[287:256]), (final_xout[255:224] + final_init[255:224]), (final_xout[223:192] + final_init[223:192]), (final_xout[191:160] + final_init[191:160]), (final_xout[159:128] + final_init[159:128]), (final_xout[127:96] + final_init[127:96]), (final_xout[95:64] + final_init[95:64]), (final_xout[63:32] + final_init[63:32]), (final_xout[31:0] + final_init[31:0])};

    assign state = state_reg;
    assign o_valid = o_valid_reg;
    assign i_ready = stage_ready[0];
    assign stage_ready[20] = o_ready;

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            state_reg <= 0;
            o_valid_reg <= 0;
        end else begin
            state_reg <= final_state;
            o_valid_reg <= final_valid;
        end
    end

endmodule

module chacha20rng (
    input clk,
    input rst_n,
    input [255:0] seed,
    input [63:0] counter,
    input [63:0] stream_id,
    input i_valid,
    input o_ready,
    output i_ready,
    output [511:0] state,
    output o_valid
);

    u_core u_core (
        .clk(clk),
        .rst_n(rst_n),
        .seed(seed),
        .stream_id(stream_id),
        .counter(counter),
        .i_valid(i_valid),
        .i_ready(i_ready),
        .o_ready(o_ready),
        .state(state),
        .o_valid(o_valid)
    );

endmodule
