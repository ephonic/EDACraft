module keccak_round (
    input clk,
    input rst_n,
    input i_valid,
    input [1599:0] state_in,
    input [4:0] round_idx,
    input o_ready,
    output i_ready,
    output reg o_valid,
    output reg [1599:0] state_out
);

    logic ready;
    logic [63:0] rc;
    logic [1599:0] next_state;
    reg valid_reg;
    reg [1599:0] state_reg;
    logic [63:0] a [0:24];
    logic [63:0] c [0:4];
    logic [63:0] d [0:4];
    logic [63:0] a_theta [0:24];
    logic [63:0] b_rhopi [0:24];
    logic [63:0] a_chi [0:24];

    assign ready = ((~valid_reg) | o_ready);
    assign i_ready = ready;
    always @(*) begin
        case (round_idx)
            0: begin
                rc = 1;
            end
            1: begin
                rc = 32898;
            end
            2: begin
                rc = 9223372036854808714;
            end
            3: begin
                rc = 9223372039002292224;
            end
            4: begin
                rc = 32907;
            end
            5: begin
                rc = 2147483649;
            end
            6: begin
                rc = 9223372039002292353;
            end
            7: begin
                rc = 9223372036854808585;
            end
            8: begin
                rc = 138;
            end
            9: begin
                rc = 136;
            end
            10: begin
                rc = 2147516425;
            end
            11: begin
                rc = 2147483658;
            end
            12: begin
                rc = 2147516555;
            end
            13: begin
                rc = 9223372036854775947;
            end
            14: begin
                rc = 9223372036854808713;
            end
            15: begin
                rc = 9223372036854808579;
            end
            16: begin
                rc = 9223372036854808578;
            end
            17: begin
                rc = 9223372036854775936;
            end
            18: begin
                rc = 32778;
            end
            19: begin
                rc = 9223372039002259466;
            end
            20: begin
                rc = 9223372039002292353;
            end
            21: begin
                rc = 9223372036854808704;
            end
            22: begin
                rc = 2147483649;
            end
            23: begin
                rc = 9223372039002292232;
            end
        endcase
    end

    always @(*) begin
        for (integer idx = 0; idx < 25; idx = idx + 1) begin
            a[idx] = state_in[(idx * 64) +: 64];
        end
        for (integer x = 0; x < 5; x = x + 1) begin
            c[x] = ((((a[x] ^ a[(x + 5)]) ^ a[(x + 10)]) ^ a[(x + 15)]) ^ a[(x + 20)]);
        end
        for (integer x = 0; x < 5; x = x + 1) begin
            d[x] = (c[((x - 1) % 5)] ^ {c[((x + 1) % 5)][62:0], c[((x + 1) % 5)][63]});
        end
        for (integer idx = 0; idx < 25; idx = idx + 1) begin
            a_theta[idx] = (a[idx] ^ d[(idx % 5)]);
        end
        b_rhopi[0] = a_theta[0];
        b_rhopi[16] = {a_theta[5][27:0], a_theta[5][63:28]};
        b_rhopi[7] = {a_theta[10][60:0], a_theta[10][63:61]};
        b_rhopi[23] = {a_theta[15][22:0], a_theta[15][63:23]};
        b_rhopi[14] = {a_theta[20][45:0], a_theta[20][63:46]};
        b_rhopi[10] = {a_theta[1][62:0], a_theta[1][63]};
        b_rhopi[1] = {a_theta[6][19:0], a_theta[6][63:20]};
        b_rhopi[17] = {a_theta[11][53:0], a_theta[11][63:54]};
        b_rhopi[8] = {a_theta[16][18:0], a_theta[16][63:19]};
        b_rhopi[24] = {a_theta[21][61:0], a_theta[21][63:62]};
        b_rhopi[20] = {a_theta[2][1:0], a_theta[2][63:2]};
        b_rhopi[11] = {a_theta[7][57:0], a_theta[7][63:58]};
        b_rhopi[2] = {a_theta[12][20:0], a_theta[12][63:21]};
        b_rhopi[18] = {a_theta[17][48:0], a_theta[17][63:49]};
        b_rhopi[9] = {a_theta[22][2:0], a_theta[22][63:3]};
        b_rhopi[5] = {a_theta[3][35:0], a_theta[3][63:36]};
        b_rhopi[21] = {a_theta[8][8:0], a_theta[8][63:9]};
        b_rhopi[12] = {a_theta[13][38:0], a_theta[13][63:39]};
        b_rhopi[3] = {a_theta[18][42:0], a_theta[18][63:43]};
        b_rhopi[19] = {a_theta[23][7:0], a_theta[23][63:8]};
        b_rhopi[15] = {a_theta[4][36:0], a_theta[4][63:37]};
        b_rhopi[6] = {a_theta[9][43:0], a_theta[9][63:44]};
        b_rhopi[22] = {a_theta[14][24:0], a_theta[14][63:25]};
        b_rhopi[13] = {a_theta[19][55:0], a_theta[19][63:56]};
        b_rhopi[4] = {a_theta[24][49:0], a_theta[24][63:50]};
        a_chi[0] = (b_rhopi[0] ^ ((~b_rhopi[1]) & b_rhopi[2]));
        a_chi[5] = (b_rhopi[5] ^ ((~b_rhopi[6]) & b_rhopi[7]));
        a_chi[10] = (b_rhopi[10] ^ ((~b_rhopi[11]) & b_rhopi[12]));
        a_chi[15] = (b_rhopi[15] ^ ((~b_rhopi[16]) & b_rhopi[17]));
        a_chi[20] = (b_rhopi[20] ^ ((~b_rhopi[21]) & b_rhopi[22]));
        a_chi[1] = (b_rhopi[1] ^ ((~b_rhopi[2]) & b_rhopi[3]));
        a_chi[6] = (b_rhopi[6] ^ ((~b_rhopi[7]) & b_rhopi[8]));
        a_chi[11] = (b_rhopi[11] ^ ((~b_rhopi[12]) & b_rhopi[13]));
        a_chi[16] = (b_rhopi[16] ^ ((~b_rhopi[17]) & b_rhopi[18]));
        a_chi[21] = (b_rhopi[21] ^ ((~b_rhopi[22]) & b_rhopi[23]));
        a_chi[2] = (b_rhopi[2] ^ ((~b_rhopi[3]) & b_rhopi[4]));
        a_chi[7] = (b_rhopi[7] ^ ((~b_rhopi[8]) & b_rhopi[9]));
        a_chi[12] = (b_rhopi[12] ^ ((~b_rhopi[13]) & b_rhopi[14]));
        a_chi[17] = (b_rhopi[17] ^ ((~b_rhopi[18]) & b_rhopi[19]));
        a_chi[22] = (b_rhopi[22] ^ ((~b_rhopi[23]) & b_rhopi[24]));
        a_chi[3] = (b_rhopi[3] ^ ((~b_rhopi[4]) & b_rhopi[0]));
        a_chi[8] = (b_rhopi[8] ^ ((~b_rhopi[9]) & b_rhopi[5]));
        a_chi[13] = (b_rhopi[13] ^ ((~b_rhopi[14]) & b_rhopi[10]));
        a_chi[18] = (b_rhopi[18] ^ ((~b_rhopi[19]) & b_rhopi[15]));
        a_chi[23] = (b_rhopi[23] ^ ((~b_rhopi[24]) & b_rhopi[20]));
        a_chi[4] = (b_rhopi[4] ^ ((~b_rhopi[0]) & b_rhopi[1]));
        a_chi[9] = (b_rhopi[9] ^ ((~b_rhopi[5]) & b_rhopi[6]));
        a_chi[14] = (b_rhopi[14] ^ ((~b_rhopi[10]) & b_rhopi[11]));
        a_chi[19] = (b_rhopi[19] ^ ((~b_rhopi[15]) & b_rhopi[16]));
        a_chi[24] = (b_rhopi[24] ^ ((~b_rhopi[20]) & b_rhopi[21]));
        next_state = {a_chi[24], a_chi[23], a_chi[22], a_chi[21], a_chi[20], a_chi[19], a_chi[18], a_chi[17], a_chi[16], a_chi[15], a_chi[14], a_chi[13], a_chi[12], a_chi[11], a_chi[10], a_chi[9], a_chi[8], a_chi[7], a_chi[6], a_chi[5], a_chi[4], a_chi[3], a_chi[2], a_chi[1], (a_chi[0] ^ rc)};
        state_out = state_reg;
        o_valid = valid_reg;
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            valid_reg <= 0;
            state_reg <= 0;
        end else begin
            if (ready) begin
                valid_reg <= i_valid;
                if (i_valid) begin
                    state_reg <= next_state;
                end
            end
        end
    end

endmodule

module sha3_256 (
    input clk,
    input rst_n,
    input i_valid,
    input [1087:0] block,
    input [7:0] block_len,
    input last_block,
    input o_ready,
    output i_ready,
    output o_valid,
    output [255:0] hash
);

    logic [1599:0] state_in;
    logic [1599:0] final_state;
    logic [7:0] padded_block [0:135];
    logic [1599:0] pipe_state [0:24];
    logic pipe_valid [0:24];
    logic pipe_ready [0:24];

    generate
        genvar i;
        for (i = 0; i < 24; i = i + 1) begin : genblk
            keccak_round u_round (
                .clk(clk),
                .rst_n(rst_n),
                .i_valid(pipe_valid[i]),
                .i_ready(pipe_ready[i]),
                .state_in(pipe_state[i]),
                .round_idx(i),
                .o_valid(pipe_valid[(i + 1)]),
                .o_ready(pipe_ready[(i + 1)]),
                .state_out(pipe_state[(i + 1)])
            );

        end
    endgenerate
    always @(*) begin
        for (integer i = 0; i < 136; i = i + 1) begin
            if ((i == 135)) begin
                padded_block[i] = ((block_len == 135) ? 134 : 128);
            end else begin
                if ((block_len == i)) begin
                    padded_block[i] = 6;
                end else begin
                    if ((block_len > i)) begin
                        padded_block[i] = block[(i * 8) +: 8];
                    end else begin
                        padded_block[i] = 0;
                    end
                end
            end
        end
    end

    assign state_in = {0, {padded_block[135], padded_block[134], padded_block[133], padded_block[132], padded_block[131], padded_block[130], padded_block[129], padded_block[128], padded_block[127], padded_block[126], padded_block[125], padded_block[124], padded_block[123], padded_block[122], padded_block[121], padded_block[120], padded_block[119], padded_block[118], padded_block[117], padded_block[116], padded_block[115], padded_block[114], padded_block[113], padded_block[112], padded_block[111], padded_block[110], padded_block[109], padded_block[108], padded_block[107], padded_block[106], padded_block[105], padded_block[104], padded_block[103], padded_block[102], padded_block[101], padded_block[100], padded_block[99], padded_block[98], padded_block[97], padded_block[96], padded_block[95], padded_block[94], padded_block[93], padded_block[92], padded_block[91], padded_block[90], padded_block[89], padded_block[88], padded_block[87], padded_block[86], padded_block[85], padded_block[84], padded_block[83], padded_block[82], padded_block[81], padded_block[80], padded_block[79], padded_block[78], padded_block[77], padded_block[76], padded_block[75], padded_block[74], padded_block[73], padded_block[72], padded_block[71], padded_block[70], padded_block[69], padded_block[68], padded_block[67], padded_block[66], padded_block[65], padded_block[64], padded_block[63], padded_block[62], padded_block[61], padded_block[60], padded_block[59], padded_block[58], padded_block[57], padded_block[56], padded_block[55], padded_block[54], padded_block[53], padded_block[52], padded_block[51], padded_block[50], padded_block[49], padded_block[48], padded_block[47], padded_block[46], padded_block[45], padded_block[44], padded_block[43], padded_block[42], padded_block[41], padded_block[40], padded_block[39], padded_block[38], padded_block[37], padded_block[36], padded_block[35], padded_block[34], padded_block[33], padded_block[32], padded_block[31], padded_block[30], padded_block[29], padded_block[28], padded_block[27], padded_block[26], padded_block[25], padded_block[24], padded_block[23], padded_block[22], padded_block[21], padded_block[20], padded_block[19], padded_block[18], padded_block[17], padded_block[16], padded_block[15], padded_block[14], padded_block[13], padded_block[12], padded_block[11], padded_block[10], padded_block[9], padded_block[8], padded_block[7], padded_block[6], padded_block[5], padded_block[4], padded_block[3], padded_block[2], padded_block[1], padded_block[0]}};

    assign pipe_state[0] = state_in;
    assign pipe_valid[0] = i_valid;

    assign final_state = pipe_state[24];
    assign hash = final_state[255:0];
    assign o_valid = pipe_valid[24];
    assign pipe_ready[24] = o_ready;
    assign i_ready = pipe_ready[0];

endmodule
