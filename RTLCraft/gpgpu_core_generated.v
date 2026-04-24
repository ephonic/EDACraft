module RegisterFile (
    input clk,
    input rst_n,
    input [4:0] rd_addr_a,
    input [4:0] rd_addr_b,
    input [4:0] wr_addr,
    input [31:0] wr_data_0,
    input [31:0] wr_data_1,
    input [31:0] wr_data_2,
    input [31:0] wr_data_3,
    input [31:0] wr_data_4,
    input [31:0] wr_data_5,
    input [31:0] wr_data_6,
    input [31:0] wr_data_7,
    input [31:0] wr_data_8,
    input [31:0] wr_data_9,
    input [31:0] wr_data_10,
    input [31:0] wr_data_11,
    input [31:0] wr_data_12,
    input [31:0] wr_data_13,
    input [31:0] wr_data_14,
    input [31:0] wr_data_15,
    input [31:0] wr_data_16,
    input [31:0] wr_data_17,
    input [31:0] wr_data_18,
    input [31:0] wr_data_19,
    input [31:0] wr_data_20,
    input [31:0] wr_data_21,
    input [31:0] wr_data_22,
    input [31:0] wr_data_23,
    input [31:0] wr_data_24,
    input [31:0] wr_data_25,
    input [31:0] wr_data_26,
    input [31:0] wr_data_27,
    input [31:0] wr_data_28,
    input [31:0] wr_data_29,
    input [31:0] wr_data_30,
    input [31:0] wr_data_31,
    input [31:0] wr_en,
    output [31:0] rd_data_a_0,
    output [31:0] rd_data_a_1,
    output [31:0] rd_data_a_2,
    output [31:0] rd_data_a_3,
    output [31:0] rd_data_a_4,
    output [31:0] rd_data_a_5,
    output [31:0] rd_data_a_6,
    output [31:0] rd_data_a_7,
    output [31:0] rd_data_a_8,
    output [31:0] rd_data_a_9,
    output [31:0] rd_data_a_10,
    output [31:0] rd_data_a_11,
    output [31:0] rd_data_a_12,
    output [31:0] rd_data_a_13,
    output [31:0] rd_data_a_14,
    output [31:0] rd_data_a_15,
    output [31:0] rd_data_a_16,
    output [31:0] rd_data_a_17,
    output [31:0] rd_data_a_18,
    output [31:0] rd_data_a_19,
    output [31:0] rd_data_a_20,
    output [31:0] rd_data_a_21,
    output [31:0] rd_data_a_22,
    output [31:0] rd_data_a_23,
    output [31:0] rd_data_a_24,
    output [31:0] rd_data_a_25,
    output [31:0] rd_data_a_26,
    output [31:0] rd_data_a_27,
    output [31:0] rd_data_a_28,
    output [31:0] rd_data_a_29,
    output [31:0] rd_data_a_30,
    output [31:0] rd_data_a_31,
    output [31:0] rd_data_b_0,
    output [31:0] rd_data_b_1,
    output [31:0] rd_data_b_2,
    output [31:0] rd_data_b_3,
    output [31:0] rd_data_b_4,
    output [31:0] rd_data_b_5,
    output [31:0] rd_data_b_6,
    output [31:0] rd_data_b_7,
    output [31:0] rd_data_b_8,
    output [31:0] rd_data_b_9,
    output [31:0] rd_data_b_10,
    output [31:0] rd_data_b_11,
    output [31:0] rd_data_b_12,
    output [31:0] rd_data_b_13,
    output [31:0] rd_data_b_14,
    output [31:0] rd_data_b_15,
    output [31:0] rd_data_b_16,
    output [31:0] rd_data_b_17,
    output [31:0] rd_data_b_18,
    output [31:0] rd_data_b_19,
    output [31:0] rd_data_b_20,
    output [31:0] rd_data_b_21,
    output [31:0] rd_data_b_22,
    output [31:0] rd_data_b_23,
    output [31:0] rd_data_b_24,
    output [31:0] rd_data_b_25,
    output [31:0] rd_data_b_26,
    output [31:0] rd_data_b_27,
    output [31:0] rd_data_b_28,
    output [31:0] rd_data_b_29,
    output [31:0] rd_data_b_30,
    output [31:0] rd_data_b_31
);

    assign rd_data_a_0 = lane_regs_0[rd_addr_a];
    assign rd_data_b_0 = lane_regs_0[rd_addr_b];
    assign rd_data_a_1 = lane_regs_1[rd_addr_a];
    assign rd_data_b_1 = lane_regs_1[rd_addr_b];
    assign rd_data_a_2 = lane_regs_2[rd_addr_a];
    assign rd_data_b_2 = lane_regs_2[rd_addr_b];
    assign rd_data_a_3 = lane_regs_3[rd_addr_a];
    assign rd_data_b_3 = lane_regs_3[rd_addr_b];
    assign rd_data_a_4 = lane_regs_4[rd_addr_a];
    assign rd_data_b_4 = lane_regs_4[rd_addr_b];
    assign rd_data_a_5 = lane_regs_5[rd_addr_a];
    assign rd_data_b_5 = lane_regs_5[rd_addr_b];
    assign rd_data_a_6 = lane_regs_6[rd_addr_a];
    assign rd_data_b_6 = lane_regs_6[rd_addr_b];
    assign rd_data_a_7 = lane_regs_7[rd_addr_a];
    assign rd_data_b_7 = lane_regs_7[rd_addr_b];
    assign rd_data_a_8 = lane_regs_8[rd_addr_a];
    assign rd_data_b_8 = lane_regs_8[rd_addr_b];
    assign rd_data_a_9 = lane_regs_9[rd_addr_a];
    assign rd_data_b_9 = lane_regs_9[rd_addr_b];
    assign rd_data_a_10 = lane_regs_10[rd_addr_a];
    assign rd_data_b_10 = lane_regs_10[rd_addr_b];
    assign rd_data_a_11 = lane_regs_11[rd_addr_a];
    assign rd_data_b_11 = lane_regs_11[rd_addr_b];
    assign rd_data_a_12 = lane_regs_12[rd_addr_a];
    assign rd_data_b_12 = lane_regs_12[rd_addr_b];
    assign rd_data_a_13 = lane_regs_13[rd_addr_a];
    assign rd_data_b_13 = lane_regs_13[rd_addr_b];
    assign rd_data_a_14 = lane_regs_14[rd_addr_a];
    assign rd_data_b_14 = lane_regs_14[rd_addr_b];
    assign rd_data_a_15 = lane_regs_15[rd_addr_a];
    assign rd_data_b_15 = lane_regs_15[rd_addr_b];
    assign rd_data_a_16 = lane_regs_16[rd_addr_a];
    assign rd_data_b_16 = lane_regs_16[rd_addr_b];
    assign rd_data_a_17 = lane_regs_17[rd_addr_a];
    assign rd_data_b_17 = lane_regs_17[rd_addr_b];
    assign rd_data_a_18 = lane_regs_18[rd_addr_a];
    assign rd_data_b_18 = lane_regs_18[rd_addr_b];
    assign rd_data_a_19 = lane_regs_19[rd_addr_a];
    assign rd_data_b_19 = lane_regs_19[rd_addr_b];
    assign rd_data_a_20 = lane_regs_20[rd_addr_a];
    assign rd_data_b_20 = lane_regs_20[rd_addr_b];
    assign rd_data_a_21 = lane_regs_21[rd_addr_a];
    assign rd_data_b_21 = lane_regs_21[rd_addr_b];
    assign rd_data_a_22 = lane_regs_22[rd_addr_a];
    assign rd_data_b_22 = lane_regs_22[rd_addr_b];
    assign rd_data_a_23 = lane_regs_23[rd_addr_a];
    assign rd_data_b_23 = lane_regs_23[rd_addr_b];
    assign rd_data_a_24 = lane_regs_24[rd_addr_a];
    assign rd_data_b_24 = lane_regs_24[rd_addr_b];
    assign rd_data_a_25 = lane_regs_25[rd_addr_a];
    assign rd_data_b_25 = lane_regs_25[rd_addr_b];
    assign rd_data_a_26 = lane_regs_26[rd_addr_a];
    assign rd_data_b_26 = lane_regs_26[rd_addr_b];
    assign rd_data_a_27 = lane_regs_27[rd_addr_a];
    assign rd_data_b_27 = lane_regs_27[rd_addr_b];
    assign rd_data_a_28 = lane_regs_28[rd_addr_a];
    assign rd_data_b_28 = lane_regs_28[rd_addr_b];
    assign rd_data_a_29 = lane_regs_29[rd_addr_a];
    assign rd_data_b_29 = lane_regs_29[rd_addr_b];
    assign rd_data_a_30 = lane_regs_30[rd_addr_a];
    assign rd_data_b_30 = lane_regs_30[rd_addr_b];
    assign rd_data_a_31 = lane_regs_31[rd_addr_a];
    assign rd_data_b_31 = lane_regs_31[rd_addr_b];

    always @(posedge clk or negedge rst_n) begin
        if (wr_en[0]) begin
            lane_regs_0[wr_addr] <= wr_data_0;
        end
        if (wr_en[1]) begin
            lane_regs_1[wr_addr] <= wr_data_1;
        end
        if (wr_en[2]) begin
            lane_regs_2[wr_addr] <= wr_data_2;
        end
        if (wr_en[3]) begin
            lane_regs_3[wr_addr] <= wr_data_3;
        end
        if (wr_en[4]) begin
            lane_regs_4[wr_addr] <= wr_data_4;
        end
        if (wr_en[5]) begin
            lane_regs_5[wr_addr] <= wr_data_5;
        end
        if (wr_en[6]) begin
            lane_regs_6[wr_addr] <= wr_data_6;
        end
        if (wr_en[7]) begin
            lane_regs_7[wr_addr] <= wr_data_7;
        end
        if (wr_en[8]) begin
            lane_regs_8[wr_addr] <= wr_data_8;
        end
        if (wr_en[9]) begin
            lane_regs_9[wr_addr] <= wr_data_9;
        end
        if (wr_en[10]) begin
            lane_regs_10[wr_addr] <= wr_data_10;
        end
        if (wr_en[11]) begin
            lane_regs_11[wr_addr] <= wr_data_11;
        end
        if (wr_en[12]) begin
            lane_regs_12[wr_addr] <= wr_data_12;
        end
        if (wr_en[13]) begin
            lane_regs_13[wr_addr] <= wr_data_13;
        end
        if (wr_en[14]) begin
            lane_regs_14[wr_addr] <= wr_data_14;
        end
        if (wr_en[15]) begin
            lane_regs_15[wr_addr] <= wr_data_15;
        end
        if (wr_en[16]) begin
            lane_regs_16[wr_addr] <= wr_data_16;
        end
        if (wr_en[17]) begin
            lane_regs_17[wr_addr] <= wr_data_17;
        end
        if (wr_en[18]) begin
            lane_regs_18[wr_addr] <= wr_data_18;
        end
        if (wr_en[19]) begin
            lane_regs_19[wr_addr] <= wr_data_19;
        end
        if (wr_en[20]) begin
            lane_regs_20[wr_addr] <= wr_data_20;
        end
        if (wr_en[21]) begin
            lane_regs_21[wr_addr] <= wr_data_21;
        end
        if (wr_en[22]) begin
            lane_regs_22[wr_addr] <= wr_data_22;
        end
        if (wr_en[23]) begin
            lane_regs_23[wr_addr] <= wr_data_23;
        end
        if (wr_en[24]) begin
            lane_regs_24[wr_addr] <= wr_data_24;
        end
        if (wr_en[25]) begin
            lane_regs_25[wr_addr] <= wr_data_25;
        end
        if (wr_en[26]) begin
            lane_regs_26[wr_addr] <= wr_data_26;
        end
        if (wr_en[27]) begin
            lane_regs_27[wr_addr] <= wr_data_27;
        end
        if (wr_en[28]) begin
            lane_regs_28[wr_addr] <= wr_data_28;
        end
        if (wr_en[29]) begin
            lane_regs_29[wr_addr] <= wr_data_29;
        end
        if (wr_en[30]) begin
            lane_regs_30[wr_addr] <= wr_data_30;
        end
        if (wr_en[31]) begin
            lane_regs_31[wr_addr] <= wr_data_31;
        end
    end

endmodule

module ALULane (
    input clk,
    input rst_n,
    input valid,
    input [5:0] op,
    input [4:0] shift_amt,
    input [31:0] src_a,
    input [31:0] src_b,
    input [31:0] src_c,
    output out_valid,
    output [31:0] result,
    output pred_out
);

    logic [31:0] int_result;
    logic [31:0] fp_result;
    logic cmp_result;
    logic pred_result;
    logic [31:0] mov_result;
    reg [31:0] result_r;
    reg pred_r;
    reg valid_r;

    assign out_valid = valid_r;
    assign result = result_r;
    assign pred_out = pred_r;
    always @(*) begin
        int_result = 0;
        fp_result = 0;
        cmp_result = 0;
        pred_result = 0;
        mov_result = 0;
        if ((op == 0)) begin
            int_result = (src_a + src_b);
        end else begin
        end
        if ((op == 1)) begin
            int_result = (src_a - src_b);
        end else begin
        end
        if ((op == 2)) begin
            int_result = (src_a * src_b);
        end else begin
        end
        if ((op == 3)) begin
            int_result = ((src_a * src_b) + src_c);
        end else begin
        end
        if ((op == 4)) begin
            int_result = (src_a & src_b);
        end else begin
        end
        if ((op == 5)) begin
            int_result = (src_a | src_b);
        end else begin
        end
        if ((op == 6)) begin
            int_result = (src_a ^ src_b);
        end else begin
        end
        if ((op == 7)) begin
            int_result = (~src_a);
        end else begin
        end
        if ((op == 8)) begin
            int_result = (src_a << shift_amt);
        end else begin
        end
        if ((op == 9)) begin
            int_result = (src_a >> shift_amt);
        end else begin
        end
        if ((op == 10)) begin
            int_result = (src_a >> shift_amt);
        end else begin
        end
        if ((op == 11)) begin
            int_result = ((src_a < src_b) ? src_a : src_b);
        end else begin
        end
        if ((op == 12)) begin
            int_result = ((src_a > src_b) ? src_a : src_b);
        end else begin
        end
        if ((op == 13)) begin
            int_result = ((src_a[31] == 1) ? (0 - src_a) : src_a);
        end else begin
        end
        if ((op == 14)) begin
            int_result = (0 - src_a);
        end else begin
        end
        if ((op == 16)) begin
            fp_result = (src_a + src_b);
        end else begin
        end
        if ((op == 17)) begin
            fp_result = (src_a - src_b);
        end else begin
        end
        if ((op == 18)) begin
            fp_result = (src_a * src_b);
        end else begin
        end
        if ((op == 19)) begin
            fp_result = ((src_a * src_b) + src_c);
        end else begin
        end
        if ((op == 20)) begin
            fp_result = ((src_a < src_b) ? src_a : src_b);
        end else begin
        end
        if ((op == 21)) begin
            fp_result = ((src_a > src_b) ? src_a : src_b);
        end else begin
        end
        if ((op == 22)) begin
            fp_result = ((src_a[31] == 1) ? (0 - src_a) : src_a);
        end else begin
        end
        if ((op == 23)) begin
            fp_result = (0 - src_a);
        end else begin
        end
        if ((op == 32)) begin
            cmp_result = (src_a == src_b);
        end else begin
        end
        if ((op == 33)) begin
            cmp_result = (src_a != src_b);
        end else begin
        end
        if ((op == 34)) begin
            cmp_result = (src_a < src_b);
        end else begin
        end
        if ((op == 35)) begin
            cmp_result = (src_a <= src_b);
        end else begin
        end
        if ((op == 36)) begin
            cmp_result = (src_a > src_b);
        end else begin
        end
        if ((op == 37)) begin
            cmp_result = (src_a >= src_b);
        end else begin
        end
        if ((op == 0)) begin
            mov_result = src_a;
        end else begin
        end
        if ((op == 1)) begin
            mov_result = (pred_out ? src_a : src_b);
        end else begin
        end
        result_r = (((op >> 4) == 2) ? 0 : (((op >> 4) == 1) ? fp_result : int_result));
        pred_r = (((op >> 4) == 2) ? cmp_result : 0);
    end

    always @(posedge clk or negedge rst_n) begin
        valid_r <= valid;
    end

endmodule

module ALUArray (
    input clk,
    input rst_n,
    input valid,
    input [5:0] op,
    input [4:0] shift_amt,
    input [31:0] src_a_0,
    input [31:0] src_a_1,
    input [31:0] src_a_2,
    input [31:0] src_a_3,
    input [31:0] src_a_4,
    input [31:0] src_a_5,
    input [31:0] src_a_6,
    input [31:0] src_a_7,
    input [31:0] src_a_8,
    input [31:0] src_a_9,
    input [31:0] src_a_10,
    input [31:0] src_a_11,
    input [31:0] src_a_12,
    input [31:0] src_a_13,
    input [31:0] src_a_14,
    input [31:0] src_a_15,
    input [31:0] src_a_16,
    input [31:0] src_a_17,
    input [31:0] src_a_18,
    input [31:0] src_a_19,
    input [31:0] src_a_20,
    input [31:0] src_a_21,
    input [31:0] src_a_22,
    input [31:0] src_a_23,
    input [31:0] src_a_24,
    input [31:0] src_a_25,
    input [31:0] src_a_26,
    input [31:0] src_a_27,
    input [31:0] src_a_28,
    input [31:0] src_a_29,
    input [31:0] src_a_30,
    input [31:0] src_a_31,
    input [31:0] src_b_0,
    input [31:0] src_b_1,
    input [31:0] src_b_2,
    input [31:0] src_b_3,
    input [31:0] src_b_4,
    input [31:0] src_b_5,
    input [31:0] src_b_6,
    input [31:0] src_b_7,
    input [31:0] src_b_8,
    input [31:0] src_b_9,
    input [31:0] src_b_10,
    input [31:0] src_b_11,
    input [31:0] src_b_12,
    input [31:0] src_b_13,
    input [31:0] src_b_14,
    input [31:0] src_b_15,
    input [31:0] src_b_16,
    input [31:0] src_b_17,
    input [31:0] src_b_18,
    input [31:0] src_b_19,
    input [31:0] src_b_20,
    input [31:0] src_b_21,
    input [31:0] src_b_22,
    input [31:0] src_b_23,
    input [31:0] src_b_24,
    input [31:0] src_b_25,
    input [31:0] src_b_26,
    input [31:0] src_b_27,
    input [31:0] src_b_28,
    input [31:0] src_b_29,
    input [31:0] src_b_30,
    input [31:0] src_b_31,
    input [31:0] src_c_0,
    input [31:0] src_c_1,
    input [31:0] src_c_2,
    input [31:0] src_c_3,
    input [31:0] src_c_4,
    input [31:0] src_c_5,
    input [31:0] src_c_6,
    input [31:0] src_c_7,
    input [31:0] src_c_8,
    input [31:0] src_c_9,
    input [31:0] src_c_10,
    input [31:0] src_c_11,
    input [31:0] src_c_12,
    input [31:0] src_c_13,
    input [31:0] src_c_14,
    input [31:0] src_c_15,
    input [31:0] src_c_16,
    input [31:0] src_c_17,
    input [31:0] src_c_18,
    input [31:0] src_c_19,
    input [31:0] src_c_20,
    input [31:0] src_c_21,
    input [31:0] src_c_22,
    input [31:0] src_c_23,
    input [31:0] src_c_24,
    input [31:0] src_c_25,
    input [31:0] src_c_26,
    input [31:0] src_c_27,
    input [31:0] src_c_28,
    input [31:0] src_c_29,
    input [31:0] src_c_30,
    input [31:0] src_c_31,
    input [31:0] pred_mask,
    output out_valid,
    output [31:0] result_0,
    output [31:0] result_1,
    output [31:0] result_2,
    output [31:0] result_3,
    output [31:0] result_4,
    output [31:0] result_5,
    output [31:0] result_6,
    output [31:0] result_7,
    output [31:0] result_8,
    output [31:0] result_9,
    output [31:0] result_10,
    output [31:0] result_11,
    output [31:0] result_12,
    output [31:0] result_13,
    output [31:0] result_14,
    output [31:0] result_15,
    output [31:0] result_16,
    output [31:0] result_17,
    output [31:0] result_18,
    output [31:0] result_19,
    output [31:0] result_20,
    output [31:0] result_21,
    output [31:0] result_22,
    output [31:0] result_23,
    output [31:0] result_24,
    output [31:0] result_25,
    output [31:0] result_26,
    output [31:0] result_27,
    output [31:0] result_28,
    output [31:0] result_29,
    output [31:0] result_30,
    output [31:0] result_31,
    output [31:0] pred_out
);

    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_0;
    assign src_b = src_b_0;
    assign src_c = src_c_0;
    assign result_0 = result;
    assign pred_out[0] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_1;
    assign src_b = src_b_1;
    assign src_c = src_c_1;
    assign result_1 = result;
    assign pred_out[1] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_2;
    assign src_b = src_b_2;
    assign src_c = src_c_2;
    assign result_2 = result;
    assign pred_out[2] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_3;
    assign src_b = src_b_3;
    assign src_c = src_c_3;
    assign result_3 = result;
    assign pred_out[3] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_4;
    assign src_b = src_b_4;
    assign src_c = src_c_4;
    assign result_4 = result;
    assign pred_out[4] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_5;
    assign src_b = src_b_5;
    assign src_c = src_c_5;
    assign result_5 = result;
    assign pred_out[5] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_6;
    assign src_b = src_b_6;
    assign src_c = src_c_6;
    assign result_6 = result;
    assign pred_out[6] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_7;
    assign src_b = src_b_7;
    assign src_c = src_c_7;
    assign result_7 = result;
    assign pred_out[7] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_8;
    assign src_b = src_b_8;
    assign src_c = src_c_8;
    assign result_8 = result;
    assign pred_out[8] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_9;
    assign src_b = src_b_9;
    assign src_c = src_c_9;
    assign result_9 = result;
    assign pred_out[9] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_10;
    assign src_b = src_b_10;
    assign src_c = src_c_10;
    assign result_10 = result;
    assign pred_out[10] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_11;
    assign src_b = src_b_11;
    assign src_c = src_c_11;
    assign result_11 = result;
    assign pred_out[11] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_12;
    assign src_b = src_b_12;
    assign src_c = src_c_12;
    assign result_12 = result;
    assign pred_out[12] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_13;
    assign src_b = src_b_13;
    assign src_c = src_c_13;
    assign result_13 = result;
    assign pred_out[13] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_14;
    assign src_b = src_b_14;
    assign src_c = src_c_14;
    assign result_14 = result;
    assign pred_out[14] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_15;
    assign src_b = src_b_15;
    assign src_c = src_c_15;
    assign result_15 = result;
    assign pred_out[15] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_16;
    assign src_b = src_b_16;
    assign src_c = src_c_16;
    assign result_16 = result;
    assign pred_out[16] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_17;
    assign src_b = src_b_17;
    assign src_c = src_c_17;
    assign result_17 = result;
    assign pred_out[17] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_18;
    assign src_b = src_b_18;
    assign src_c = src_c_18;
    assign result_18 = result;
    assign pred_out[18] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_19;
    assign src_b = src_b_19;
    assign src_c = src_c_19;
    assign result_19 = result;
    assign pred_out[19] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_20;
    assign src_b = src_b_20;
    assign src_c = src_c_20;
    assign result_20 = result;
    assign pred_out[20] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_21;
    assign src_b = src_b_21;
    assign src_c = src_c_21;
    assign result_21 = result;
    assign pred_out[21] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_22;
    assign src_b = src_b_22;
    assign src_c = src_c_22;
    assign result_22 = result;
    assign pred_out[22] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_23;
    assign src_b = src_b_23;
    assign src_c = src_c_23;
    assign result_23 = result;
    assign pred_out[23] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_24;
    assign src_b = src_b_24;
    assign src_c = src_c_24;
    assign result_24 = result;
    assign pred_out[24] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_25;
    assign src_b = src_b_25;
    assign src_c = src_c_25;
    assign result_25 = result;
    assign pred_out[25] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_26;
    assign src_b = src_b_26;
    assign src_c = src_c_26;
    assign result_26 = result;
    assign pred_out[26] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_27;
    assign src_b = src_b_27;
    assign src_c = src_c_27;
    assign result_27 = result;
    assign pred_out[27] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_28;
    assign src_b = src_b_28;
    assign src_c = src_c_28;
    assign result_28 = result;
    assign pred_out[28] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_29;
    assign src_b = src_b_29;
    assign src_c = src_c_29;
    assign result_29 = result;
    assign pred_out[29] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_30;
    assign src_b = src_b_30;
    assign src_c = src_c_30;
    assign result_30 = result;
    assign pred_out[30] = pred_out;
    assign clk = clk;
    assign rst_n = rst_n;
    assign valid = valid;
    assign op = op;
    assign shift_amt = shift_amt;
    assign src_a = src_a_31;
    assign src_b = src_b_31;
    assign src_c = src_c_31;
    assign result_31 = result;
    assign pred_out[31] = pred_out;
    assign out_valid = out_valid;
    ALULane alu_lane_0 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_1 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_2 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_3 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_4 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_5 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_6 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_7 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_8 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_9 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_10 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_11 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_12 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_13 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_14 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_15 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_16 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_17 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_18 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_19 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_20 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_21 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_22 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_23 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_24 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_25 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_26 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_27 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_28 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_29 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_30 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

    ALULane alu_lane_31 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .shift_amt(shift_amt),
        .out_valid(out_valid),
        .pred_out(pred_out)
    );

endmodule

module SFULane (
    input clk,
    input rst_n,
    input valid,
    input [5:0] op,
    input [31:0] src,
    output out_valid,
    output [31:0] result
);

    reg [15:0] lut_sin [0:255];
    reg [15:0] lut_cos [0:255];
    reg [15:0] lut_log2 [0:255];
    reg [15:0] lut_exp2 [0:255];
    reg [15:0] lut_recip [0:255];
    reg [15:0] lut_rsqrt [0:255];

    logic [7:0] idx;
    logic [15:0] lut_val;
    reg pipe_v0;
    reg pipe_v1;
    reg [15:0] pipe_val0;
    reg [15:0] pipe_val1;

    assign out_valid = pipe_v1;
    assign result = pipe_val1;
    assign idx = ((((src >> 8) + 128) > 255) ? 255 : ((((src >> 8) + 128) < 0) ? 0 : ((src >> 8) + 128)[7:0]));

    always @(*) begin
        lut_val = 0;
        if ((op == 0)) begin
            lut_val = lut_sin[idx];
        end else begin
        end
        if ((op == 1)) begin
            lut_val = lut_cos[idx];
        end else begin
        end
        if ((op == 2)) begin
            lut_val = lut_log2[idx];
        end else begin
        end
        if ((op == 3)) begin
            lut_val = lut_exp2[idx];
        end else begin
        end
        if ((op == 4)) begin
            lut_val = lut_recip[idx];
        end else begin
        end
        if ((op == 5)) begin
            lut_val = lut_rsqrt[idx];
        end else begin
        end
    end

    always @(posedge clk or negedge rst_n) begin
        pipe_v0 <= valid;
        pipe_val0 <= lut_val;
        pipe_v1 <= pipe_v0;
        pipe_val1 <= pipe_val0;
    end

endmodule

module SFUArray (
    input clk,
    input rst_n,
    input valid,
    input [5:0] op,
    input [31:0] src_0,
    input [31:0] src_1,
    input [31:0] src_2,
    input [31:0] src_3,
    input [31:0] src_4,
    input [31:0] src_5,
    input [31:0] src_6,
    input [31:0] src_7,
    input [31:0] src_8,
    input [31:0] src_9,
    input [31:0] src_10,
    input [31:0] src_11,
    input [31:0] src_12,
    input [31:0] src_13,
    input [31:0] src_14,
    input [31:0] src_15,
    input [31:0] src_16,
    input [31:0] src_17,
    input [31:0] src_18,
    input [31:0] src_19,
    input [31:0] src_20,
    input [31:0] src_21,
    input [31:0] src_22,
    input [31:0] src_23,
    input [31:0] src_24,
    input [31:0] src_25,
    input [31:0] src_26,
    input [31:0] src_27,
    input [31:0] src_28,
    input [31:0] src_29,
    input [31:0] src_30,
    input [31:0] src_31,
    output out_valid,
    output [31:0] result_0,
    output [31:0] result_1,
    output [31:0] result_2,
    output [31:0] result_3,
    output [31:0] result_4,
    output [31:0] result_5,
    output [31:0] result_6,
    output [31:0] result_7,
    output [31:0] result_8,
    output [31:0] result_9,
    output [31:0] result_10,
    output [31:0] result_11,
    output [31:0] result_12,
    output [31:0] result_13,
    output [31:0] result_14,
    output [31:0] result_15,
    output [31:0] result_16,
    output [31:0] result_17,
    output [31:0] result_18,
    output [31:0] result_19,
    output [31:0] result_20,
    output [31:0] result_21,
    output [31:0] result_22,
    output [31:0] result_23,
    output [31:0] result_24,
    output [31:0] result_25,
    output [31:0] result_26,
    output [31:0] result_27,
    output [31:0] result_28,
    output [31:0] result_29,
    output [31:0] result_30,
    output [31:0] result_31
);

    reg [31:0] req_buf_0;
    reg [31:0] req_buf_1;
    reg [31:0] req_buf_2;
    reg [31:0] req_buf_3;
    reg [31:0] req_buf_4;
    reg [31:0] req_buf_5;
    reg [31:0] req_buf_6;
    reg [31:0] req_buf_7;
    reg [31:0] req_buf_8;
    reg [31:0] req_buf_9;
    reg [31:0] req_buf_10;
    reg [31:0] req_buf_11;
    reg [31:0] req_buf_12;
    reg [31:0] req_buf_13;
    reg [31:0] req_buf_14;
    reg [31:0] req_buf_15;
    reg [31:0] req_buf_16;
    reg [31:0] req_buf_17;
    reg [31:0] req_buf_18;
    reg [31:0] req_buf_19;
    reg [31:0] req_buf_20;
    reg [31:0] req_buf_21;
    reg [31:0] req_buf_22;
    reg [31:0] req_buf_23;
    reg [31:0] req_buf_24;
    reg [31:0] req_buf_25;
    reg [31:0] req_buf_26;
    reg [31:0] req_buf_27;
    reg [31:0] req_buf_28;
    reg [31:0] req_buf_29;
    reg [31:0] req_buf_30;
    reg [31:0] req_buf_31;
    reg [31:0] res_buf_0;
    reg [31:0] res_buf_1;
    reg [31:0] res_buf_2;
    reg [31:0] res_buf_3;
    reg [31:0] res_buf_4;
    reg [31:0] res_buf_5;
    reg [31:0] res_buf_6;
    reg [31:0] res_buf_7;
    reg [31:0] res_buf_8;
    reg [31:0] res_buf_9;
    reg [31:0] res_buf_10;
    reg [31:0] res_buf_11;
    reg [31:0] res_buf_12;
    reg [31:0] res_buf_13;
    reg [31:0] res_buf_14;
    reg [31:0] res_buf_15;
    reg [31:0] res_buf_16;
    reg [31:0] res_buf_17;
    reg [31:0] res_buf_18;
    reg [31:0] res_buf_19;
    reg [31:0] res_buf_20;
    reg [31:0] res_buf_21;
    reg [31:0] res_buf_22;
    reg [31:0] res_buf_23;
    reg [31:0] res_buf_24;
    reg [31:0] res_buf_25;
    reg [31:0] res_buf_26;
    reg [31:0] res_buf_27;
    reg [31:0] res_buf_28;
    reg [31:0] res_buf_29;
    reg [31:0] res_buf_30;
    reg [31:0] res_buf_31;
    reg [1:0] state;
    reg [2:0] dispatch_cnt;
    reg [1:0] wait_cnt;
    reg [4:0] lane_tag_0;
    reg [4:0] lane_tag_1;
    reg [4:0] lane_tag_2;
    reg [4:0] lane_tag_3;

    assign clk = clk;
    assign rst_n = rst_n;
    assign op = op;
    assign clk = clk;
    assign rst_n = rst_n;
    assign op = op;
    assign clk = clk;
    assign rst_n = rst_n;
    assign op = op;
    assign clk = clk;
    assign rst_n = rst_n;
    assign op = op;
    assign result_0 = res_buf_0;
    assign result_1 = res_buf_1;
    assign result_2 = res_buf_2;
    assign result_3 = res_buf_3;
    assign result_4 = res_buf_4;
    assign result_5 = res_buf_5;
    assign result_6 = res_buf_6;
    assign result_7 = res_buf_7;
    assign result_8 = res_buf_8;
    assign result_9 = res_buf_9;
    assign result_10 = res_buf_10;
    assign result_11 = res_buf_11;
    assign result_12 = res_buf_12;
    assign result_13 = res_buf_13;
    assign result_14 = res_buf_14;
    assign result_15 = res_buf_15;
    assign result_16 = res_buf_16;
    assign result_17 = res_buf_17;
    assign result_18 = res_buf_18;
    assign result_19 = res_buf_19;
    assign result_20 = res_buf_20;
    assign result_21 = res_buf_21;
    assign result_22 = res_buf_22;
    assign result_23 = res_buf_23;
    assign result_24 = res_buf_24;
    assign result_25 = res_buf_25;
    assign result_26 = res_buf_26;
    assign result_27 = res_buf_27;
    assign result_28 = res_buf_28;
    assign result_29 = res_buf_29;
    assign result_30 = res_buf_30;
    assign result_31 = res_buf_31;
    assign out_valid = (state == 3);
    SFULane sfu_lane_0 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .out_valid(out_valid)
    );

    SFULane sfu_lane_1 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .out_valid(out_valid)
    );

    SFULane sfu_lane_2 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .out_valid(out_valid)
    );

    SFULane sfu_lane_3 (
        .clk(clk),
        .rst_n(rst_n),
        .valid(valid),
        .op(op),
        .out_valid(out_valid)
    );

    always @(*) begin
        valid = ((state == 1) & (((dispatch_cnt * 4) + 0) < 32));
        case (((dispatch_cnt * 4) + 0))
            31: src = req_buf_31;
            30: src = req_buf_30;
            29: src = req_buf_29;
            28: src = req_buf_28;
            27: src = req_buf_27;
            26: src = req_buf_26;
            25: src = req_buf_25;
            24: src = req_buf_24;
            23: src = req_buf_23;
            22: src = req_buf_22;
            21: src = req_buf_21;
            20: src = req_buf_20;
            19: src = req_buf_19;
            18: src = req_buf_18;
            17: src = req_buf_17;
            16: src = req_buf_16;
            15: src = req_buf_15;
            14: src = req_buf_14;
            13: src = req_buf_13;
            12: src = req_buf_12;
            11: src = req_buf_11;
            10: src = req_buf_10;
            9: src = req_buf_9;
            8: src = req_buf_8;
            7: src = req_buf_7;
            6: src = req_buf_6;
            5: src = req_buf_5;
            4: src = req_buf_4;
            3: src = req_buf_3;
            2: src = req_buf_2;
            1: src = req_buf_1;
            default: src = req_buf_0;
        endcase
        valid = ((state == 1) & (((dispatch_cnt * 4) + 1) < 32));
        case (((dispatch_cnt * 4) + 1))
            31: src = req_buf_31;
            30: src = req_buf_30;
            29: src = req_buf_29;
            28: src = req_buf_28;
            27: src = req_buf_27;
            26: src = req_buf_26;
            25: src = req_buf_25;
            24: src = req_buf_24;
            23: src = req_buf_23;
            22: src = req_buf_22;
            21: src = req_buf_21;
            20: src = req_buf_20;
            19: src = req_buf_19;
            18: src = req_buf_18;
            17: src = req_buf_17;
            16: src = req_buf_16;
            15: src = req_buf_15;
            14: src = req_buf_14;
            13: src = req_buf_13;
            12: src = req_buf_12;
            11: src = req_buf_11;
            10: src = req_buf_10;
            9: src = req_buf_9;
            8: src = req_buf_8;
            7: src = req_buf_7;
            6: src = req_buf_6;
            5: src = req_buf_5;
            4: src = req_buf_4;
            3: src = req_buf_3;
            2: src = req_buf_2;
            1: src = req_buf_1;
            default: src = req_buf_0;
        endcase
        valid = ((state == 1) & (((dispatch_cnt * 4) + 2) < 32));
        case (((dispatch_cnt * 4) + 2))
            31: src = req_buf_31;
            30: src = req_buf_30;
            29: src = req_buf_29;
            28: src = req_buf_28;
            27: src = req_buf_27;
            26: src = req_buf_26;
            25: src = req_buf_25;
            24: src = req_buf_24;
            23: src = req_buf_23;
            22: src = req_buf_22;
            21: src = req_buf_21;
            20: src = req_buf_20;
            19: src = req_buf_19;
            18: src = req_buf_18;
            17: src = req_buf_17;
            16: src = req_buf_16;
            15: src = req_buf_15;
            14: src = req_buf_14;
            13: src = req_buf_13;
            12: src = req_buf_12;
            11: src = req_buf_11;
            10: src = req_buf_10;
            9: src = req_buf_9;
            8: src = req_buf_8;
            7: src = req_buf_7;
            6: src = req_buf_6;
            5: src = req_buf_5;
            4: src = req_buf_4;
            3: src = req_buf_3;
            2: src = req_buf_2;
            1: src = req_buf_1;
            default: src = req_buf_0;
        endcase
        valid = ((state == 1) & (((dispatch_cnt * 4) + 3) < 32));
        case (((dispatch_cnt * 4) + 3))
            31: src = req_buf_31;
            30: src = req_buf_30;
            29: src = req_buf_29;
            28: src = req_buf_28;
            27: src = req_buf_27;
            26: src = req_buf_26;
            25: src = req_buf_25;
            24: src = req_buf_24;
            23: src = req_buf_23;
            22: src = req_buf_22;
            21: src = req_buf_21;
            20: src = req_buf_20;
            19: src = req_buf_19;
            18: src = req_buf_18;
            17: src = req_buf_17;
            16: src = req_buf_16;
            15: src = req_buf_15;
            14: src = req_buf_14;
            13: src = req_buf_13;
            12: src = req_buf_12;
            11: src = req_buf_11;
            10: src = req_buf_10;
            9: src = req_buf_9;
            8: src = req_buf_8;
            7: src = req_buf_7;
            6: src = req_buf_6;
            5: src = req_buf_5;
            4: src = req_buf_4;
            3: src = req_buf_3;
            2: src = req_buf_2;
            1: src = req_buf_1;
            default: src = req_buf_0;
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            state <= 0;
            dispatch_cnt <= 0;
            wait_cnt <= 0;
            lane_tag_0 <= 0;
            lane_tag_1 <= 0;
            lane_tag_2 <= 0;
            lane_tag_3 <= 0;
        end else begin
            if ((state == 0)) begin
                if (valid) begin
                    state <= 1;
                    dispatch_cnt <= 0;
                    wait_cnt <= 0;
                    req_buf_0 <= src_0;
                    req_buf_1 <= src_1;
                    req_buf_2 <= src_2;
                    req_buf_3 <= src_3;
                    req_buf_4 <= src_4;
                    req_buf_5 <= src_5;
                    req_buf_6 <= src_6;
                    req_buf_7 <= src_7;
                    req_buf_8 <= src_8;
                    req_buf_9 <= src_9;
                    req_buf_10 <= src_10;
                    req_buf_11 <= src_11;
                    req_buf_12 <= src_12;
                    req_buf_13 <= src_13;
                    req_buf_14 <= src_14;
                    req_buf_15 <= src_15;
                    req_buf_16 <= src_16;
                    req_buf_17 <= src_17;
                    req_buf_18 <= src_18;
                    req_buf_19 <= src_19;
                    req_buf_20 <= src_20;
                    req_buf_21 <= src_21;
                    req_buf_22 <= src_22;
                    req_buf_23 <= src_23;
                    req_buf_24 <= src_24;
                    req_buf_25 <= src_25;
                    req_buf_26 <= src_26;
                    req_buf_27 <= src_27;
                    req_buf_28 <= src_28;
                    req_buf_29 <= src_29;
                    req_buf_30 <= src_30;
                    req_buf_31 <= src_31;
                end
            end
            if ((state == 1)) begin
                lane_tag_0 <= ((dispatch_cnt * 4) + 0);
                lane_tag_1 <= ((dispatch_cnt * 4) + 1);
                lane_tag_2 <= ((dispatch_cnt * 4) + 2);
                lane_tag_3 <= ((dispatch_cnt * 4) + 3);
                dispatch_cnt <= (dispatch_cnt + 1);
                if ((dispatch_cnt == 7)) begin
                    state <= 2;
                end
            end
            if ((state == 2)) begin
                wait_cnt <= (wait_cnt + 1);
                if ((wait_cnt == 3)) begin
                    state <= 3;
                end
            end
            if ((state == 3)) begin
                state <= 0;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (out_valid) begin
            if ((lane_tag_0 == 0)) begin
                res_buf_0 <= result;
            end
            if ((lane_tag_0 == 1)) begin
                res_buf_1 <= result;
            end
            if ((lane_tag_0 == 2)) begin
                res_buf_2 <= result;
            end
            if ((lane_tag_0 == 3)) begin
                res_buf_3 <= result;
            end
            if ((lane_tag_0 == 4)) begin
                res_buf_4 <= result;
            end
            if ((lane_tag_0 == 5)) begin
                res_buf_5 <= result;
            end
            if ((lane_tag_0 == 6)) begin
                res_buf_6 <= result;
            end
            if ((lane_tag_0 == 7)) begin
                res_buf_7 <= result;
            end
            if ((lane_tag_0 == 8)) begin
                res_buf_8 <= result;
            end
            if ((lane_tag_0 == 9)) begin
                res_buf_9 <= result;
            end
            if ((lane_tag_0 == 10)) begin
                res_buf_10 <= result;
            end
            if ((lane_tag_0 == 11)) begin
                res_buf_11 <= result;
            end
            if ((lane_tag_0 == 12)) begin
                res_buf_12 <= result;
            end
            if ((lane_tag_0 == 13)) begin
                res_buf_13 <= result;
            end
            if ((lane_tag_0 == 14)) begin
                res_buf_14 <= result;
            end
            if ((lane_tag_0 == 15)) begin
                res_buf_15 <= result;
            end
            if ((lane_tag_0 == 16)) begin
                res_buf_16 <= result;
            end
            if ((lane_tag_0 == 17)) begin
                res_buf_17 <= result;
            end
            if ((lane_tag_0 == 18)) begin
                res_buf_18 <= result;
            end
            if ((lane_tag_0 == 19)) begin
                res_buf_19 <= result;
            end
            if ((lane_tag_0 == 20)) begin
                res_buf_20 <= result;
            end
            if ((lane_tag_0 == 21)) begin
                res_buf_21 <= result;
            end
            if ((lane_tag_0 == 22)) begin
                res_buf_22 <= result;
            end
            if ((lane_tag_0 == 23)) begin
                res_buf_23 <= result;
            end
            if ((lane_tag_0 == 24)) begin
                res_buf_24 <= result;
            end
            if ((lane_tag_0 == 25)) begin
                res_buf_25 <= result;
            end
            if ((lane_tag_0 == 26)) begin
                res_buf_26 <= result;
            end
            if ((lane_tag_0 == 27)) begin
                res_buf_27 <= result;
            end
            if ((lane_tag_0 == 28)) begin
                res_buf_28 <= result;
            end
            if ((lane_tag_0 == 29)) begin
                res_buf_29 <= result;
            end
            if ((lane_tag_0 == 30)) begin
                res_buf_30 <= result;
            end
            if ((lane_tag_0 == 31)) begin
                res_buf_31 <= result;
            end
        end
        if (out_valid) begin
            if ((lane_tag_1 == 0)) begin
                res_buf_0 <= result;
            end
            if ((lane_tag_1 == 1)) begin
                res_buf_1 <= result;
            end
            if ((lane_tag_1 == 2)) begin
                res_buf_2 <= result;
            end
            if ((lane_tag_1 == 3)) begin
                res_buf_3 <= result;
            end
            if ((lane_tag_1 == 4)) begin
                res_buf_4 <= result;
            end
            if ((lane_tag_1 == 5)) begin
                res_buf_5 <= result;
            end
            if ((lane_tag_1 == 6)) begin
                res_buf_6 <= result;
            end
            if ((lane_tag_1 == 7)) begin
                res_buf_7 <= result;
            end
            if ((lane_tag_1 == 8)) begin
                res_buf_8 <= result;
            end
            if ((lane_tag_1 == 9)) begin
                res_buf_9 <= result;
            end
            if ((lane_tag_1 == 10)) begin
                res_buf_10 <= result;
            end
            if ((lane_tag_1 == 11)) begin
                res_buf_11 <= result;
            end
            if ((lane_tag_1 == 12)) begin
                res_buf_12 <= result;
            end
            if ((lane_tag_1 == 13)) begin
                res_buf_13 <= result;
            end
            if ((lane_tag_1 == 14)) begin
                res_buf_14 <= result;
            end
            if ((lane_tag_1 == 15)) begin
                res_buf_15 <= result;
            end
            if ((lane_tag_1 == 16)) begin
                res_buf_16 <= result;
            end
            if ((lane_tag_1 == 17)) begin
                res_buf_17 <= result;
            end
            if ((lane_tag_1 == 18)) begin
                res_buf_18 <= result;
            end
            if ((lane_tag_1 == 19)) begin
                res_buf_19 <= result;
            end
            if ((lane_tag_1 == 20)) begin
                res_buf_20 <= result;
            end
            if ((lane_tag_1 == 21)) begin
                res_buf_21 <= result;
            end
            if ((lane_tag_1 == 22)) begin
                res_buf_22 <= result;
            end
            if ((lane_tag_1 == 23)) begin
                res_buf_23 <= result;
            end
            if ((lane_tag_1 == 24)) begin
                res_buf_24 <= result;
            end
            if ((lane_tag_1 == 25)) begin
                res_buf_25 <= result;
            end
            if ((lane_tag_1 == 26)) begin
                res_buf_26 <= result;
            end
            if ((lane_tag_1 == 27)) begin
                res_buf_27 <= result;
            end
            if ((lane_tag_1 == 28)) begin
                res_buf_28 <= result;
            end
            if ((lane_tag_1 == 29)) begin
                res_buf_29 <= result;
            end
            if ((lane_tag_1 == 30)) begin
                res_buf_30 <= result;
            end
            if ((lane_tag_1 == 31)) begin
                res_buf_31 <= result;
            end
        end
        if (out_valid) begin
            if ((lane_tag_2 == 0)) begin
                res_buf_0 <= result;
            end
            if ((lane_tag_2 == 1)) begin
                res_buf_1 <= result;
            end
            if ((lane_tag_2 == 2)) begin
                res_buf_2 <= result;
            end
            if ((lane_tag_2 == 3)) begin
                res_buf_3 <= result;
            end
            if ((lane_tag_2 == 4)) begin
                res_buf_4 <= result;
            end
            if ((lane_tag_2 == 5)) begin
                res_buf_5 <= result;
            end
            if ((lane_tag_2 == 6)) begin
                res_buf_6 <= result;
            end
            if ((lane_tag_2 == 7)) begin
                res_buf_7 <= result;
            end
            if ((lane_tag_2 == 8)) begin
                res_buf_8 <= result;
            end
            if ((lane_tag_2 == 9)) begin
                res_buf_9 <= result;
            end
            if ((lane_tag_2 == 10)) begin
                res_buf_10 <= result;
            end
            if ((lane_tag_2 == 11)) begin
                res_buf_11 <= result;
            end
            if ((lane_tag_2 == 12)) begin
                res_buf_12 <= result;
            end
            if ((lane_tag_2 == 13)) begin
                res_buf_13 <= result;
            end
            if ((lane_tag_2 == 14)) begin
                res_buf_14 <= result;
            end
            if ((lane_tag_2 == 15)) begin
                res_buf_15 <= result;
            end
            if ((lane_tag_2 == 16)) begin
                res_buf_16 <= result;
            end
            if ((lane_tag_2 == 17)) begin
                res_buf_17 <= result;
            end
            if ((lane_tag_2 == 18)) begin
                res_buf_18 <= result;
            end
            if ((lane_tag_2 == 19)) begin
                res_buf_19 <= result;
            end
            if ((lane_tag_2 == 20)) begin
                res_buf_20 <= result;
            end
            if ((lane_tag_2 == 21)) begin
                res_buf_21 <= result;
            end
            if ((lane_tag_2 == 22)) begin
                res_buf_22 <= result;
            end
            if ((lane_tag_2 == 23)) begin
                res_buf_23 <= result;
            end
            if ((lane_tag_2 == 24)) begin
                res_buf_24 <= result;
            end
            if ((lane_tag_2 == 25)) begin
                res_buf_25 <= result;
            end
            if ((lane_tag_2 == 26)) begin
                res_buf_26 <= result;
            end
            if ((lane_tag_2 == 27)) begin
                res_buf_27 <= result;
            end
            if ((lane_tag_2 == 28)) begin
                res_buf_28 <= result;
            end
            if ((lane_tag_2 == 29)) begin
                res_buf_29 <= result;
            end
            if ((lane_tag_2 == 30)) begin
                res_buf_30 <= result;
            end
            if ((lane_tag_2 == 31)) begin
                res_buf_31 <= result;
            end
        end
        if (out_valid) begin
            if ((lane_tag_3 == 0)) begin
                res_buf_0 <= result;
            end
            if ((lane_tag_3 == 1)) begin
                res_buf_1 <= result;
            end
            if ((lane_tag_3 == 2)) begin
                res_buf_2 <= result;
            end
            if ((lane_tag_3 == 3)) begin
                res_buf_3 <= result;
            end
            if ((lane_tag_3 == 4)) begin
                res_buf_4 <= result;
            end
            if ((lane_tag_3 == 5)) begin
                res_buf_5 <= result;
            end
            if ((lane_tag_3 == 6)) begin
                res_buf_6 <= result;
            end
            if ((lane_tag_3 == 7)) begin
                res_buf_7 <= result;
            end
            if ((lane_tag_3 == 8)) begin
                res_buf_8 <= result;
            end
            if ((lane_tag_3 == 9)) begin
                res_buf_9 <= result;
            end
            if ((lane_tag_3 == 10)) begin
                res_buf_10 <= result;
            end
            if ((lane_tag_3 == 11)) begin
                res_buf_11 <= result;
            end
            if ((lane_tag_3 == 12)) begin
                res_buf_12 <= result;
            end
            if ((lane_tag_3 == 13)) begin
                res_buf_13 <= result;
            end
            if ((lane_tag_3 == 14)) begin
                res_buf_14 <= result;
            end
            if ((lane_tag_3 == 15)) begin
                res_buf_15 <= result;
            end
            if ((lane_tag_3 == 16)) begin
                res_buf_16 <= result;
            end
            if ((lane_tag_3 == 17)) begin
                res_buf_17 <= result;
            end
            if ((lane_tag_3 == 18)) begin
                res_buf_18 <= result;
            end
            if ((lane_tag_3 == 19)) begin
                res_buf_19 <= result;
            end
            if ((lane_tag_3 == 20)) begin
                res_buf_20 <= result;
            end
            if ((lane_tag_3 == 21)) begin
                res_buf_21 <= result;
            end
            if ((lane_tag_3 == 22)) begin
                res_buf_22 <= result;
            end
            if ((lane_tag_3 == 23)) begin
                res_buf_23 <= result;
            end
            if ((lane_tag_3 == 24)) begin
                res_buf_24 <= result;
            end
            if ((lane_tag_3 == 25)) begin
                res_buf_25 <= result;
            end
            if ((lane_tag_3 == 26)) begin
                res_buf_26 <= result;
            end
            if ((lane_tag_3 == 27)) begin
                res_buf_27 <= result;
            end
            if ((lane_tag_3 == 28)) begin
                res_buf_28 <= result;
            end
            if ((lane_tag_3 == 29)) begin
                res_buf_29 <= result;
            end
            if ((lane_tag_3 == 30)) begin
                res_buf_30 <= result;
            end
            if ((lane_tag_3 == 31)) begin
                res_buf_31 <= result;
            end
        end
    end

endmodule

module TensorCore (
    input clk,
    input rst_n,
    input start,
    input [5:0] op,
    input load_valid,
    input [31:0] load_data_0,
    input [31:0] load_data_1,
    input [31:0] load_data_2,
    input [31:0] load_data_3,
    input [31:0] load_data_4,
    input [31:0] load_data_5,
    input [31:0] load_data_6,
    input [31:0] load_data_7,
    input [31:0] load_data_8,
    input [31:0] load_data_9,
    input [31:0] load_data_10,
    input [31:0] load_data_11,
    input [31:0] load_data_12,
    input [31:0] load_data_13,
    input [31:0] load_data_14,
    input [31:0] load_data_15,
    input [31:0] load_data_16,
    input [31:0] load_data_17,
    input [31:0] load_data_18,
    input [31:0] load_data_19,
    input [31:0] load_data_20,
    input [31:0] load_data_21,
    input [31:0] load_data_22,
    input [31:0] load_data_23,
    input [31:0] load_data_24,
    input [31:0] load_data_25,
    input [31:0] load_data_26,
    input [31:0] load_data_27,
    input [31:0] load_data_28,
    input [31:0] load_data_29,
    input [31:0] load_data_30,
    input [31:0] load_data_31,
    input load_done,
    input store_ready,
    output done,
    output busy,
    output store_valid,
    output [31:0] store_data_0,
    output [31:0] store_data_1,
    output [31:0] store_data_2,
    output [31:0] store_data_3,
    output [31:0] store_data_4,
    output [31:0] store_data_5,
    output [31:0] store_data_6,
    output [31:0] store_data_7,
    output [31:0] store_data_8,
    output [31:0] store_data_9,
    output [31:0] store_data_10,
    output [31:0] store_data_11,
    output [31:0] store_data_12,
    output [31:0] store_data_13,
    output [31:0] store_data_14,
    output [31:0] store_data_15
);

    reg [31:0] buf_a [0:15];
    reg [31:0] buf_b [0:15];
    reg [31:0] buf_c [0:15];
    reg [31:0] buf_d [0:15];

    logic [31:0] a_read_0;
    logic [31:0] a_read_1;
    logic [31:0] a_read_2;
    logic [31:0] a_read_3;
    logic [31:0] a_read_4;
    logic [31:0] a_read_5;
    logic [31:0] a_read_6;
    logic [31:0] a_read_7;
    logic [31:0] a_read_8;
    logic [31:0] a_read_9;
    logic [31:0] a_read_10;
    logic [31:0] a_read_11;
    logic [31:0] a_read_12;
    logic [31:0] a_read_13;
    logic [31:0] a_read_14;
    logic [31:0] a_read_15;
    logic [31:0] b_read_0;
    logic [31:0] b_read_1;
    logic [31:0] b_read_2;
    logic [31:0] b_read_3;
    logic [31:0] b_read_4;
    logic [31:0] b_read_5;
    logic [31:0] b_read_6;
    logic [31:0] b_read_7;
    logic [31:0] b_read_8;
    logic [31:0] b_read_9;
    logic [31:0] b_read_10;
    logic [31:0] b_read_11;
    logic [31:0] b_read_12;
    logic [31:0] b_read_13;
    logic [31:0] b_read_14;
    logic [31:0] b_read_15;
    logic [31:0] c_read_0;
    logic [31:0] c_read_1;
    logic [31:0] c_read_2;
    logic [31:0] c_read_3;
    logic [31:0] c_read_4;
    logic [31:0] c_read_5;
    logic [31:0] c_read_6;
    logic [31:0] c_read_7;
    logic [31:0] c_read_8;
    logic [31:0] c_read_9;
    logic [31:0] c_read_10;
    logic [31:0] c_read_11;
    logic [31:0] c_read_12;
    logic [31:0] c_read_13;
    logic [31:0] c_read_14;
    logic [31:0] c_read_15;
    logic compute_done;
    reg [2:0] state;
    reg [3:0] load_cnt;
    reg store_cnt;

    assign compute_done = 0;
    assign busy = (state != 0);
    assign done = (state == 6);
    assign store_valid = (state == 5);
    assign store_data_0 = buf_d[0];
    assign store_data_1 = buf_d[1];
    assign store_data_2 = buf_d[2];
    assign store_data_3 = buf_d[3];
    assign store_data_4 = buf_d[4];
    assign store_data_5 = buf_d[5];
    assign store_data_6 = buf_d[6];
    assign store_data_7 = buf_d[7];
    assign store_data_8 = buf_d[8];
    assign store_data_9 = buf_d[9];
    assign store_data_10 = buf_d[10];
    assign store_data_11 = buf_d[11];
    assign store_data_12 = buf_d[12];
    assign store_data_13 = buf_d[13];
    assign store_data_14 = buf_d[14];
    assign store_data_15 = buf_d[15];
    assign a_read_0 = buf_a[0];
    assign b_read_0 = buf_b[0];
    assign c_read_0 = buf_c[0];
    assign a_read_1 = buf_a[1];
    assign b_read_1 = buf_b[1];
    assign c_read_1 = buf_c[1];
    assign a_read_2 = buf_a[2];
    assign b_read_2 = buf_b[2];
    assign c_read_2 = buf_c[2];
    assign a_read_3 = buf_a[3];
    assign b_read_3 = buf_b[3];
    assign c_read_3 = buf_c[3];
    assign a_read_4 = buf_a[4];
    assign b_read_4 = buf_b[4];
    assign c_read_4 = buf_c[4];
    assign a_read_5 = buf_a[5];
    assign b_read_5 = buf_b[5];
    assign c_read_5 = buf_c[5];
    assign a_read_6 = buf_a[6];
    assign b_read_6 = buf_b[6];
    assign c_read_6 = buf_c[6];
    assign a_read_7 = buf_a[7];
    assign b_read_7 = buf_b[7];
    assign c_read_7 = buf_c[7];
    assign a_read_8 = buf_a[8];
    assign b_read_8 = buf_b[8];
    assign c_read_8 = buf_c[8];
    assign a_read_9 = buf_a[9];
    assign b_read_9 = buf_b[9];
    assign c_read_9 = buf_c[9];
    assign a_read_10 = buf_a[10];
    assign b_read_10 = buf_b[10];
    assign c_read_10 = buf_c[10];
    assign a_read_11 = buf_a[11];
    assign b_read_11 = buf_b[11];
    assign c_read_11 = buf_c[11];
    assign a_read_12 = buf_a[12];
    assign b_read_12 = buf_b[12];
    assign c_read_12 = buf_c[12];
    assign a_read_13 = buf_a[13];
    assign b_read_13 = buf_b[13];
    assign c_read_13 = buf_c[13];
    assign a_read_14 = buf_a[14];
    assign b_read_14 = buf_b[14];
    assign c_read_14 = buf_c[14];
    assign a_read_15 = buf_a[15];
    assign b_read_15 = buf_b[15];
    assign c_read_15 = buf_c[15];

    always @(*) begin
        buf_d[0] = (((((0 + (a_read_0 * b_read_0)) + (a_read_1 * b_read_4)) + (a_read_2 * b_read_8)) + (a_read_3 * b_read_12)) + c_read_0);
        buf_d[1] = (((((0 + (a_read_0 * b_read_1)) + (a_read_1 * b_read_5)) + (a_read_2 * b_read_9)) + (a_read_3 * b_read_13)) + c_read_1);
        buf_d[2] = (((((0 + (a_read_0 * b_read_2)) + (a_read_1 * b_read_6)) + (a_read_2 * b_read_10)) + (a_read_3 * b_read_14)) + c_read_2);
        buf_d[3] = (((((0 + (a_read_0 * b_read_3)) + (a_read_1 * b_read_7)) + (a_read_2 * b_read_11)) + (a_read_3 * b_read_15)) + c_read_3);
        buf_d[4] = (((((0 + (a_read_4 * b_read_0)) + (a_read_5 * b_read_4)) + (a_read_6 * b_read_8)) + (a_read_7 * b_read_12)) + c_read_4);
        buf_d[5] = (((((0 + (a_read_4 * b_read_1)) + (a_read_5 * b_read_5)) + (a_read_6 * b_read_9)) + (a_read_7 * b_read_13)) + c_read_5);
        buf_d[6] = (((((0 + (a_read_4 * b_read_2)) + (a_read_5 * b_read_6)) + (a_read_6 * b_read_10)) + (a_read_7 * b_read_14)) + c_read_6);
        buf_d[7] = (((((0 + (a_read_4 * b_read_3)) + (a_read_5 * b_read_7)) + (a_read_6 * b_read_11)) + (a_read_7 * b_read_15)) + c_read_7);
        buf_d[8] = (((((0 + (a_read_8 * b_read_0)) + (a_read_9 * b_read_4)) + (a_read_10 * b_read_8)) + (a_read_11 * b_read_12)) + c_read_8);
        buf_d[9] = (((((0 + (a_read_8 * b_read_1)) + (a_read_9 * b_read_5)) + (a_read_10 * b_read_9)) + (a_read_11 * b_read_13)) + c_read_9);
        buf_d[10] = (((((0 + (a_read_8 * b_read_2)) + (a_read_9 * b_read_6)) + (a_read_10 * b_read_10)) + (a_read_11 * b_read_14)) + c_read_10);
        buf_d[11] = (((((0 + (a_read_8 * b_read_3)) + (a_read_9 * b_read_7)) + (a_read_10 * b_read_11)) + (a_read_11 * b_read_15)) + c_read_11);
        buf_d[12] = (((((0 + (a_read_12 * b_read_0)) + (a_read_13 * b_read_4)) + (a_read_14 * b_read_8)) + (a_read_15 * b_read_12)) + c_read_12);
        buf_d[13] = (((((0 + (a_read_12 * b_read_1)) + (a_read_13 * b_read_5)) + (a_read_14 * b_read_9)) + (a_read_15 * b_read_13)) + c_read_13);
        buf_d[14] = (((((0 + (a_read_12 * b_read_2)) + (a_read_13 * b_read_6)) + (a_read_14 * b_read_10)) + (a_read_15 * b_read_14)) + c_read_14);
        buf_d[15] = (((((0 + (a_read_12 * b_read_3)) + (a_read_13 * b_read_7)) + (a_read_14 * b_read_11)) + (a_read_15 * b_read_15)) + c_read_15);
        compute_done = 1;
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            state <= 0;
            load_cnt <= 0;
            store_cnt <= 0;
        end else begin
            if ((state == 0)) begin
                if (start) begin
                    state <= 1;
                    load_cnt <= 0;
                end
            end
            if ((state == 1)) begin
                if (load_valid) begin
                    if ((((load_cnt * 16) + 0) < 16)) begin
                        buf_a[((load_cnt * 16) + 0)] <= load_data_0;
                    end
                    if ((((load_cnt * 16) + 1) < 16)) begin
                        buf_a[((load_cnt * 16) + 1)] <= load_data_1;
                    end
                    if ((((load_cnt * 16) + 2) < 16)) begin
                        buf_a[((load_cnt * 16) + 2)] <= load_data_2;
                    end
                    if ((((load_cnt * 16) + 3) < 16)) begin
                        buf_a[((load_cnt * 16) + 3)] <= load_data_3;
                    end
                    if ((((load_cnt * 16) + 4) < 16)) begin
                        buf_a[((load_cnt * 16) + 4)] <= load_data_4;
                    end
                    if ((((load_cnt * 16) + 5) < 16)) begin
                        buf_a[((load_cnt * 16) + 5)] <= load_data_5;
                    end
                    if ((((load_cnt * 16) + 6) < 16)) begin
                        buf_a[((load_cnt * 16) + 6)] <= load_data_6;
                    end
                    if ((((load_cnt * 16) + 7) < 16)) begin
                        buf_a[((load_cnt * 16) + 7)] <= load_data_7;
                    end
                    if ((((load_cnt * 16) + 8) < 16)) begin
                        buf_a[((load_cnt * 16) + 8)] <= load_data_8;
                    end
                    if ((((load_cnt * 16) + 9) < 16)) begin
                        buf_a[((load_cnt * 16) + 9)] <= load_data_9;
                    end
                    if ((((load_cnt * 16) + 10) < 16)) begin
                        buf_a[((load_cnt * 16) + 10)] <= load_data_10;
                    end
                    if ((((load_cnt * 16) + 11) < 16)) begin
                        buf_a[((load_cnt * 16) + 11)] <= load_data_11;
                    end
                    if ((((load_cnt * 16) + 12) < 16)) begin
                        buf_a[((load_cnt * 16) + 12)] <= load_data_12;
                    end
                    if ((((load_cnt * 16) + 13) < 16)) begin
                        buf_a[((load_cnt * 16) + 13)] <= load_data_13;
                    end
                    if ((((load_cnt * 16) + 14) < 16)) begin
                        buf_a[((load_cnt * 16) + 14)] <= load_data_14;
                    end
                    if ((((load_cnt * 16) + 15) < 16)) begin
                        buf_a[((load_cnt * 16) + 15)] <= load_data_15;
                    end
                    load_cnt <= (load_cnt + 1);
                end
                if (load_done) begin
                    state <= 2;
                    load_cnt <= 0;
                end
            end
            if ((state == 2)) begin
                if (load_valid) begin
                    if ((((load_cnt * 16) + 0) < 16)) begin
                        buf_b[((load_cnt * 16) + 0)] <= load_data_0;
                    end
                    if ((((load_cnt * 16) + 1) < 16)) begin
                        buf_b[((load_cnt * 16) + 1)] <= load_data_1;
                    end
                    if ((((load_cnt * 16) + 2) < 16)) begin
                        buf_b[((load_cnt * 16) + 2)] <= load_data_2;
                    end
                    if ((((load_cnt * 16) + 3) < 16)) begin
                        buf_b[((load_cnt * 16) + 3)] <= load_data_3;
                    end
                    if ((((load_cnt * 16) + 4) < 16)) begin
                        buf_b[((load_cnt * 16) + 4)] <= load_data_4;
                    end
                    if ((((load_cnt * 16) + 5) < 16)) begin
                        buf_b[((load_cnt * 16) + 5)] <= load_data_5;
                    end
                    if ((((load_cnt * 16) + 6) < 16)) begin
                        buf_b[((load_cnt * 16) + 6)] <= load_data_6;
                    end
                    if ((((load_cnt * 16) + 7) < 16)) begin
                        buf_b[((load_cnt * 16) + 7)] <= load_data_7;
                    end
                    if ((((load_cnt * 16) + 8) < 16)) begin
                        buf_b[((load_cnt * 16) + 8)] <= load_data_8;
                    end
                    if ((((load_cnt * 16) + 9) < 16)) begin
                        buf_b[((load_cnt * 16) + 9)] <= load_data_9;
                    end
                    if ((((load_cnt * 16) + 10) < 16)) begin
                        buf_b[((load_cnt * 16) + 10)] <= load_data_10;
                    end
                    if ((((load_cnt * 16) + 11) < 16)) begin
                        buf_b[((load_cnt * 16) + 11)] <= load_data_11;
                    end
                    if ((((load_cnt * 16) + 12) < 16)) begin
                        buf_b[((load_cnt * 16) + 12)] <= load_data_12;
                    end
                    if ((((load_cnt * 16) + 13) < 16)) begin
                        buf_b[((load_cnt * 16) + 13)] <= load_data_13;
                    end
                    if ((((load_cnt * 16) + 14) < 16)) begin
                        buf_b[((load_cnt * 16) + 14)] <= load_data_14;
                    end
                    if ((((load_cnt * 16) + 15) < 16)) begin
                        buf_b[((load_cnt * 16) + 15)] <= load_data_15;
                    end
                    load_cnt <= (load_cnt + 1);
                end
                if (load_done) begin
                    state <= 3;
                    load_cnt <= 0;
                end
            end
            if ((state == 3)) begin
                if (load_valid) begin
                    if ((((load_cnt * 16) + 0) < 16)) begin
                        buf_c[((load_cnt * 16) + 0)] <= load_data_0;
                    end
                    if ((((load_cnt * 16) + 1) < 16)) begin
                        buf_c[((load_cnt * 16) + 1)] <= load_data_1;
                    end
                    if ((((load_cnt * 16) + 2) < 16)) begin
                        buf_c[((load_cnt * 16) + 2)] <= load_data_2;
                    end
                    if ((((load_cnt * 16) + 3) < 16)) begin
                        buf_c[((load_cnt * 16) + 3)] <= load_data_3;
                    end
                    if ((((load_cnt * 16) + 4) < 16)) begin
                        buf_c[((load_cnt * 16) + 4)] <= load_data_4;
                    end
                    if ((((load_cnt * 16) + 5) < 16)) begin
                        buf_c[((load_cnt * 16) + 5)] <= load_data_5;
                    end
                    if ((((load_cnt * 16) + 6) < 16)) begin
                        buf_c[((load_cnt * 16) + 6)] <= load_data_6;
                    end
                    if ((((load_cnt * 16) + 7) < 16)) begin
                        buf_c[((load_cnt * 16) + 7)] <= load_data_7;
                    end
                    if ((((load_cnt * 16) + 8) < 16)) begin
                        buf_c[((load_cnt * 16) + 8)] <= load_data_8;
                    end
                    if ((((load_cnt * 16) + 9) < 16)) begin
                        buf_c[((load_cnt * 16) + 9)] <= load_data_9;
                    end
                    if ((((load_cnt * 16) + 10) < 16)) begin
                        buf_c[((load_cnt * 16) + 10)] <= load_data_10;
                    end
                    if ((((load_cnt * 16) + 11) < 16)) begin
                        buf_c[((load_cnt * 16) + 11)] <= load_data_11;
                    end
                    if ((((load_cnt * 16) + 12) < 16)) begin
                        buf_c[((load_cnt * 16) + 12)] <= load_data_12;
                    end
                    if ((((load_cnt * 16) + 13) < 16)) begin
                        buf_c[((load_cnt * 16) + 13)] <= load_data_13;
                    end
                    if ((((load_cnt * 16) + 14) < 16)) begin
                        buf_c[((load_cnt * 16) + 14)] <= load_data_14;
                    end
                    if ((((load_cnt * 16) + 15) < 16)) begin
                        buf_c[((load_cnt * 16) + 15)] <= load_data_15;
                    end
                    load_cnt <= (load_cnt + 1);
                end
                if (load_done) begin
                    state <= 4;
                end
            end
            if ((state == 4)) begin
                state <= 5;
                store_cnt <= 0;
            end
            if ((state == 5)) begin
                if (store_ready) begin
                    store_cnt <= (store_cnt + 1);
                end
                if ((store_cnt == 1)) begin
                    state <= 6;
                end
            end
            if ((state == 6)) begin
                state <= 0;
            end
        end
    end

endmodule

module WarpScheduler (
    input clk,
    input rst_n,
    input launch_valid,
    input [1:0] launch_warps,
    input [15:0] launch_pc,
    input fetch_ready,
    input issue_ready,
    input branch_valid,
    input [1:0] branch_warp,
    input [31:0] branch_taken_mask,
    input [31:0] branch_not_taken_mask,
    input [15:0] branch_taken_pc,
    input [15:0] branch_not_taken_pc,
    input [15:0] branch_reconverge_pc,
    input wb_valid,
    input [1:0] wb_warp,
    input [31:0] wb_mask,
    output kernel_done,
    output [1:0] fetch_warp,
    output [15:0] fetch_pc,
    output fetch_valid,
    output [1:0] issue_warp,
    output [15:0] issue_pc,
    output [31:0] issue_mask,
    output issue_valid
);

    logic [1:0] next_warp;
    logic next_valid;
    reg [15:0] warp_pc_0;
    reg [15:0] warp_pc_1;
    reg [15:0] warp_pc_2;
    reg [15:0] warp_pc_3;
    reg [31:0] warp_active_0;
    reg [31:0] warp_active_1;
    reg [31:0] warp_active_2;
    reg [31:0] warp_active_3;
    reg warp_valid_0;
    reg warp_valid_1;
    reg warp_valid_2;
    reg warp_valid_3;
    reg warp_done_0;
    reg warp_done_1;
    reg warp_done_2;
    reg warp_done_3;
    reg [2:0] stack_ptr_0;
    reg [2:0] stack_ptr_1;
    reg [2:0] stack_ptr_2;
    reg [2:0] stack_ptr_3;
    reg [1:0] rr_ptr;

    assign fetch_valid = (next_valid & fetch_ready);
    assign fetch_warp = next_warp;
    always @(*) begin
        case (next_warp)
            3: fetch_pc = warp_pc_3;
            2: fetch_pc = warp_pc_2;
            1: fetch_pc = warp_pc_1;
            default: fetch_pc = warp_pc_0;
        endcase
    end
    assign issue_valid = (next_valid & issue_ready);
    assign issue_warp = next_warp;
    always @(*) begin
        case (next_warp)
            3: issue_pc = warp_pc_3;
            2: issue_pc = warp_pc_2;
            1: issue_pc = warp_pc_1;
            default: issue_pc = warp_pc_0;
        endcase
    end
    always @(*) begin
        case (next_warp)
            3: issue_mask = warp_active_3;
            2: issue_mask = warp_active_2;
            1: issue_mask = warp_active_1;
            default: issue_mask = warp_active_0;
        endcase
    end
    assign kernel_done = ((((1 & ((~warp_valid_0) | warp_done_0)) & ((~warp_valid_1) | warp_done_1)) & ((~warp_valid_2) | warp_done_2)) & ((~warp_valid_3) | warp_done_3));
    always @(*) begin
        if ((((-1 & ((((rr_ptr + 1) % 4) == 3) ? warp_valid_3 : ((((rr_ptr + 1) % 4) == 2) ? warp_valid_2 : ((((rr_ptr + 1) % 4) == 1) ? warp_valid_1 : warp_valid_0)))) & (~((((rr_ptr + 1) % 4) == 3) ? warp_done_3 : ((((rr_ptr + 1) % 4) == 2) ? warp_done_2 : ((((rr_ptr + 1) % 4) == 1) ? warp_done_1 : warp_done_0))))) & (((((rr_ptr + 1) % 4) == 3) ? warp_active_3 : ((((rr_ptr + 1) % 4) == 2) ? warp_active_2 : ((((rr_ptr + 1) % 4) == 1) ? warp_active_1 : warp_active_0))) != 0))) begin
        end else begin
        end
        if ((((-2 & ((((rr_ptr + 2) % 4) == 3) ? warp_valid_3 : ((((rr_ptr + 2) % 4) == 2) ? warp_valid_2 : ((((rr_ptr + 2) % 4) == 1) ? warp_valid_1 : warp_valid_0)))) & (~((((rr_ptr + 2) % 4) == 3) ? warp_done_3 : ((((rr_ptr + 2) % 4) == 2) ? warp_done_2 : ((((rr_ptr + 2) % 4) == 1) ? warp_done_1 : warp_done_0))))) & (((((rr_ptr + 2) % 4) == 3) ? warp_active_3 : ((((rr_ptr + 2) % 4) == 2) ? warp_active_2 : ((((rr_ptr + 2) % 4) == 1) ? warp_active_1 : warp_active_0))) != 0))) begin
        end else begin
        end
        if ((((-2 & ((((rr_ptr + 3) % 4) == 3) ? warp_valid_3 : ((((rr_ptr + 3) % 4) == 2) ? warp_valid_2 : ((((rr_ptr + 3) % 4) == 1) ? warp_valid_1 : warp_valid_0)))) & (~((((rr_ptr + 3) % 4) == 3) ? warp_done_3 : ((((rr_ptr + 3) % 4) == 2) ? warp_done_2 : ((((rr_ptr + 3) % 4) == 1) ? warp_done_1 : warp_done_0))))) & (((((rr_ptr + 3) % 4) == 3) ? warp_active_3 : ((((rr_ptr + 3) % 4) == 2) ? warp_active_2 : ((((rr_ptr + 3) % 4) == 1) ? warp_active_1 : warp_active_0))) != 0))) begin
        end else begin
        end
        if ((((-2 & ((((rr_ptr + 4) % 4) == 3) ? warp_valid_3 : ((((rr_ptr + 4) % 4) == 2) ? warp_valid_2 : ((((rr_ptr + 4) % 4) == 1) ? warp_valid_1 : warp_valid_0)))) & (~((((rr_ptr + 4) % 4) == 3) ? warp_done_3 : ((((rr_ptr + 4) % 4) == 2) ? warp_done_2 : ((((rr_ptr + 4) % 4) == 1) ? warp_done_1 : warp_done_0))))) & (((((rr_ptr + 4) % 4) == 3) ? warp_active_3 : ((((rr_ptr + 4) % 4) == 2) ? warp_active_2 : ((((rr_ptr + 4) % 4) == 1) ? warp_active_1 : warp_active_0))) != 0))) begin
        end else begin
        end
        next_warp = ((rr_ptr + 4) % 4);
        next_valid = 1;
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            rr_ptr <= 0;
            warp_valid_0 <= 0;
            warp_done_0 <= 0;
            warp_active_0 <= 0;
            stack_ptr_0 <= 0;
            warp_valid_1 <= 0;
            warp_done_1 <= 0;
            warp_active_1 <= 0;
            stack_ptr_1 <= 0;
            warp_valid_2 <= 0;
            warp_done_2 <= 0;
            warp_active_2 <= 0;
            stack_ptr_2 <= 0;
            warp_valid_3 <= 0;
            warp_done_3 <= 0;
            warp_active_3 <= 0;
            stack_ptr_3 <= 0;
        end else begin
            if (launch_valid) begin
                if ((launch_warps > 0)) begin
                    warp_valid_0 <= 1;
                    warp_done_0 <= 0;
                    warp_pc_0 <= launch_pc;
                    warp_active_0 <= 4294967295;
                    stack_ptr_0 <= 0;
                end else begin
                    warp_valid_0 <= 0;
                end
                if ((launch_warps > 1)) begin
                    warp_valid_1 <= 1;
                    warp_done_1 <= 0;
                    warp_pc_1 <= launch_pc;
                    warp_active_1 <= 4294967295;
                    stack_ptr_1 <= 0;
                end else begin
                    warp_valid_1 <= 0;
                end
                if ((launch_warps > 2)) begin
                    warp_valid_2 <= 1;
                    warp_done_2 <= 0;
                    warp_pc_2 <= launch_pc;
                    warp_active_2 <= 4294967295;
                    stack_ptr_2 <= 0;
                end else begin
                    warp_valid_2 <= 0;
                end
                if ((launch_warps > 3)) begin
                    warp_valid_3 <= 1;
                    warp_done_3 <= 0;
                    warp_pc_3 <= launch_pc;
                    warp_active_3 <= 4294967295;
                    stack_ptr_3 <= 0;
                end else begin
                    warp_valid_3 <= 0;
                end
            end
            if (((issue_ready & next_valid) & fetch_ready)) begin
                rr_ptr <= next_warp;
                if ((next_warp == 0)) begin
                    warp_pc_0 <= (warp_pc_0 + 1);
                end
                if ((next_warp == 1)) begin
                    warp_pc_1 <= (warp_pc_1 + 1);
                end
                if ((next_warp == 2)) begin
                    warp_pc_2 <= (warp_pc_2 + 1);
                end
                if ((next_warp == 3)) begin
                    warp_pc_3 <= (warp_pc_3 + 1);
                end
            end
            if (branch_valid) begin
                if ((branch_warp == 0)) begin
                    if (((branch_taken_mask != 0) & (branch_not_taken_mask != 0))) begin
                        if ((stack_ptr_0 < 8)) begin
                            if ((stack_ptr_0 == 0)) begin
                                stack_pc_0_0 <= branch_not_taken_pc;
                                stack_mask_0_0 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_0 == 1)) begin
                                stack_pc_0_1 <= branch_not_taken_pc;
                                stack_mask_0_1 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_0 == 2)) begin
                                stack_pc_0_2 <= branch_not_taken_pc;
                                stack_mask_0_2 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_0 == 3)) begin
                                stack_pc_0_3 <= branch_not_taken_pc;
                                stack_mask_0_3 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_0 == 4)) begin
                                stack_pc_0_4 <= branch_not_taken_pc;
                                stack_mask_0_4 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_0 == 5)) begin
                                stack_pc_0_5 <= branch_not_taken_pc;
                                stack_mask_0_5 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_0 == 6)) begin
                                stack_pc_0_6 <= branch_not_taken_pc;
                                stack_mask_0_6 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_0 == 7)) begin
                                stack_pc_0_7 <= branch_not_taken_pc;
                                stack_mask_0_7 <= branch_not_taken_mask;
                            end
                            stack_ptr_0 <= (stack_ptr_0 + 1);
                        end
                        warp_pc_0 <= branch_taken_pc;
                        warp_active_0 <= branch_taken_mask;
                    end else begin
                        if ((branch_taken_mask != 0)) begin
                            warp_pc_0 <= branch_taken_pc;
                            warp_active_0 <= branch_taken_mask;
                        end else begin
                            warp_pc_0 <= branch_not_taken_pc;
                            warp_active_0 <= branch_not_taken_mask;
                        end
                    end
                end
                if ((branch_warp == 1)) begin
                    if (((branch_taken_mask != 0) & (branch_not_taken_mask != 0))) begin
                        if ((stack_ptr_1 < 8)) begin
                            if ((stack_ptr_1 == 0)) begin
                                stack_pc_1_0 <= branch_not_taken_pc;
                                stack_mask_1_0 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_1 == 1)) begin
                                stack_pc_1_1 <= branch_not_taken_pc;
                                stack_mask_1_1 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_1 == 2)) begin
                                stack_pc_1_2 <= branch_not_taken_pc;
                                stack_mask_1_2 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_1 == 3)) begin
                                stack_pc_1_3 <= branch_not_taken_pc;
                                stack_mask_1_3 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_1 == 4)) begin
                                stack_pc_1_4 <= branch_not_taken_pc;
                                stack_mask_1_4 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_1 == 5)) begin
                                stack_pc_1_5 <= branch_not_taken_pc;
                                stack_mask_1_5 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_1 == 6)) begin
                                stack_pc_1_6 <= branch_not_taken_pc;
                                stack_mask_1_6 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_1 == 7)) begin
                                stack_pc_1_7 <= branch_not_taken_pc;
                                stack_mask_1_7 <= branch_not_taken_mask;
                            end
                            stack_ptr_1 <= (stack_ptr_1 + 1);
                        end
                        warp_pc_1 <= branch_taken_pc;
                        warp_active_1 <= branch_taken_mask;
                    end else begin
                        if ((branch_taken_mask != 0)) begin
                            warp_pc_1 <= branch_taken_pc;
                            warp_active_1 <= branch_taken_mask;
                        end else begin
                            warp_pc_1 <= branch_not_taken_pc;
                            warp_active_1 <= branch_not_taken_mask;
                        end
                    end
                end
                if ((branch_warp == 2)) begin
                    if (((branch_taken_mask != 0) & (branch_not_taken_mask != 0))) begin
                        if ((stack_ptr_2 < 8)) begin
                            if ((stack_ptr_2 == 0)) begin
                                stack_pc_2_0 <= branch_not_taken_pc;
                                stack_mask_2_0 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_2 == 1)) begin
                                stack_pc_2_1 <= branch_not_taken_pc;
                                stack_mask_2_1 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_2 == 2)) begin
                                stack_pc_2_2 <= branch_not_taken_pc;
                                stack_mask_2_2 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_2 == 3)) begin
                                stack_pc_2_3 <= branch_not_taken_pc;
                                stack_mask_2_3 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_2 == 4)) begin
                                stack_pc_2_4 <= branch_not_taken_pc;
                                stack_mask_2_4 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_2 == 5)) begin
                                stack_pc_2_5 <= branch_not_taken_pc;
                                stack_mask_2_5 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_2 == 6)) begin
                                stack_pc_2_6 <= branch_not_taken_pc;
                                stack_mask_2_6 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_2 == 7)) begin
                                stack_pc_2_7 <= branch_not_taken_pc;
                                stack_mask_2_7 <= branch_not_taken_mask;
                            end
                            stack_ptr_2 <= (stack_ptr_2 + 1);
                        end
                        warp_pc_2 <= branch_taken_pc;
                        warp_active_2 <= branch_taken_mask;
                    end else begin
                        if ((branch_taken_mask != 0)) begin
                            warp_pc_2 <= branch_taken_pc;
                            warp_active_2 <= branch_taken_mask;
                        end else begin
                            warp_pc_2 <= branch_not_taken_pc;
                            warp_active_2 <= branch_not_taken_mask;
                        end
                    end
                end
                if ((branch_warp == 3)) begin
                    if (((branch_taken_mask != 0) & (branch_not_taken_mask != 0))) begin
                        if ((stack_ptr_3 < 8)) begin
                            if ((stack_ptr_3 == 0)) begin
                                stack_pc_3_0 <= branch_not_taken_pc;
                                stack_mask_3_0 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_3 == 1)) begin
                                stack_pc_3_1 <= branch_not_taken_pc;
                                stack_mask_3_1 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_3 == 2)) begin
                                stack_pc_3_2 <= branch_not_taken_pc;
                                stack_mask_3_2 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_3 == 3)) begin
                                stack_pc_3_3 <= branch_not_taken_pc;
                                stack_mask_3_3 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_3 == 4)) begin
                                stack_pc_3_4 <= branch_not_taken_pc;
                                stack_mask_3_4 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_3 == 5)) begin
                                stack_pc_3_5 <= branch_not_taken_pc;
                                stack_mask_3_5 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_3 == 6)) begin
                                stack_pc_3_6 <= branch_not_taken_pc;
                                stack_mask_3_6 <= branch_not_taken_mask;
                            end
                            if ((stack_ptr_3 == 7)) begin
                                stack_pc_3_7 <= branch_not_taken_pc;
                                stack_mask_3_7 <= branch_not_taken_mask;
                            end
                            stack_ptr_3 <= (stack_ptr_3 + 1);
                        end
                        warp_pc_3 <= branch_taken_pc;
                        warp_active_3 <= branch_taken_mask;
                    end else begin
                        if ((branch_taken_mask != 0)) begin
                            warp_pc_3 <= branch_taken_pc;
                            warp_active_3 <= branch_taken_mask;
                        end else begin
                            warp_pc_3 <= branch_not_taken_pc;
                            warp_active_3 <= branch_not_taken_mask;
                        end
                    end
                end
            end
            if (((warp_valid_0 & (~warp_done_0)) & (warp_pc_0 == branch_reconverge_pc))) begin
                if ((stack_ptr_0 > 0)) begin
                    if (((stack_ptr_0 - 1) == 0)) begin
                        warp_pc_0 <= stack_pc_0_0;
                        warp_active_0 <= stack_mask_0_0;
                    end
                    if (((stack_ptr_0 - 1) == 1)) begin
                        warp_pc_0 <= stack_pc_0_1;
                        warp_active_0 <= stack_mask_0_1;
                    end
                    if (((stack_ptr_0 - 1) == 2)) begin
                        warp_pc_0 <= stack_pc_0_2;
                        warp_active_0 <= stack_mask_0_2;
                    end
                    if (((stack_ptr_0 - 1) == 3)) begin
                        warp_pc_0 <= stack_pc_0_3;
                        warp_active_0 <= stack_mask_0_3;
                    end
                    if (((stack_ptr_0 - 1) == 4)) begin
                        warp_pc_0 <= stack_pc_0_4;
                        warp_active_0 <= stack_mask_0_4;
                    end
                    if (((stack_ptr_0 - 1) == 5)) begin
                        warp_pc_0 <= stack_pc_0_5;
                        warp_active_0 <= stack_mask_0_5;
                    end
                    if (((stack_ptr_0 - 1) == 6)) begin
                        warp_pc_0 <= stack_pc_0_6;
                        warp_active_0 <= stack_mask_0_6;
                    end
                    if (((stack_ptr_0 - 1) == 7)) begin
                        warp_pc_0 <= stack_pc_0_7;
                        warp_active_0 <= stack_mask_0_7;
                    end
                    stack_ptr_0 <= (stack_ptr_0 - 1);
                end else begin
                    if ((warp_active_0 == 0)) begin
                        warp_done_0 <= 1;
                    end
                end
            end
            if (((warp_valid_1 & (~warp_done_1)) & (warp_pc_1 == branch_reconverge_pc))) begin
                if ((stack_ptr_1 > 0)) begin
                    if (((stack_ptr_1 - 1) == 0)) begin
                        warp_pc_1 <= stack_pc_1_0;
                        warp_active_1 <= stack_mask_1_0;
                    end
                    if (((stack_ptr_1 - 1) == 1)) begin
                        warp_pc_1 <= stack_pc_1_1;
                        warp_active_1 <= stack_mask_1_1;
                    end
                    if (((stack_ptr_1 - 1) == 2)) begin
                        warp_pc_1 <= stack_pc_1_2;
                        warp_active_1 <= stack_mask_1_2;
                    end
                    if (((stack_ptr_1 - 1) == 3)) begin
                        warp_pc_1 <= stack_pc_1_3;
                        warp_active_1 <= stack_mask_1_3;
                    end
                    if (((stack_ptr_1 - 1) == 4)) begin
                        warp_pc_1 <= stack_pc_1_4;
                        warp_active_1 <= stack_mask_1_4;
                    end
                    if (((stack_ptr_1 - 1) == 5)) begin
                        warp_pc_1 <= stack_pc_1_5;
                        warp_active_1 <= stack_mask_1_5;
                    end
                    if (((stack_ptr_1 - 1) == 6)) begin
                        warp_pc_1 <= stack_pc_1_6;
                        warp_active_1 <= stack_mask_1_6;
                    end
                    if (((stack_ptr_1 - 1) == 7)) begin
                        warp_pc_1 <= stack_pc_1_7;
                        warp_active_1 <= stack_mask_1_7;
                    end
                    stack_ptr_1 <= (stack_ptr_1 - 1);
                end else begin
                    if ((warp_active_1 == 0)) begin
                        warp_done_1 <= 1;
                    end
                end
            end
            if (((warp_valid_2 & (~warp_done_2)) & (warp_pc_2 == branch_reconverge_pc))) begin
                if ((stack_ptr_2 > 0)) begin
                    if (((stack_ptr_2 - 1) == 0)) begin
                        warp_pc_2 <= stack_pc_2_0;
                        warp_active_2 <= stack_mask_2_0;
                    end
                    if (((stack_ptr_2 - 1) == 1)) begin
                        warp_pc_2 <= stack_pc_2_1;
                        warp_active_2 <= stack_mask_2_1;
                    end
                    if (((stack_ptr_2 - 1) == 2)) begin
                        warp_pc_2 <= stack_pc_2_2;
                        warp_active_2 <= stack_mask_2_2;
                    end
                    if (((stack_ptr_2 - 1) == 3)) begin
                        warp_pc_2 <= stack_pc_2_3;
                        warp_active_2 <= stack_mask_2_3;
                    end
                    if (((stack_ptr_2 - 1) == 4)) begin
                        warp_pc_2 <= stack_pc_2_4;
                        warp_active_2 <= stack_mask_2_4;
                    end
                    if (((stack_ptr_2 - 1) == 5)) begin
                        warp_pc_2 <= stack_pc_2_5;
                        warp_active_2 <= stack_mask_2_5;
                    end
                    if (((stack_ptr_2 - 1) == 6)) begin
                        warp_pc_2 <= stack_pc_2_6;
                        warp_active_2 <= stack_mask_2_6;
                    end
                    if (((stack_ptr_2 - 1) == 7)) begin
                        warp_pc_2 <= stack_pc_2_7;
                        warp_active_2 <= stack_mask_2_7;
                    end
                    stack_ptr_2 <= (stack_ptr_2 - 1);
                end else begin
                    if ((warp_active_2 == 0)) begin
                        warp_done_2 <= 1;
                    end
                end
            end
            if (((warp_valid_3 & (~warp_done_3)) & (warp_pc_3 == branch_reconverge_pc))) begin
                if ((stack_ptr_3 > 0)) begin
                    if (((stack_ptr_3 - 1) == 0)) begin
                        warp_pc_3 <= stack_pc_3_0;
                        warp_active_3 <= stack_mask_3_0;
                    end
                    if (((stack_ptr_3 - 1) == 1)) begin
                        warp_pc_3 <= stack_pc_3_1;
                        warp_active_3 <= stack_mask_3_1;
                    end
                    if (((stack_ptr_3 - 1) == 2)) begin
                        warp_pc_3 <= stack_pc_3_2;
                        warp_active_3 <= stack_mask_3_2;
                    end
                    if (((stack_ptr_3 - 1) == 3)) begin
                        warp_pc_3 <= stack_pc_3_3;
                        warp_active_3 <= stack_mask_3_3;
                    end
                    if (((stack_ptr_3 - 1) == 4)) begin
                        warp_pc_3 <= stack_pc_3_4;
                        warp_active_3 <= stack_mask_3_4;
                    end
                    if (((stack_ptr_3 - 1) == 5)) begin
                        warp_pc_3 <= stack_pc_3_5;
                        warp_active_3 <= stack_mask_3_5;
                    end
                    if (((stack_ptr_3 - 1) == 6)) begin
                        warp_pc_3 <= stack_pc_3_6;
                        warp_active_3 <= stack_mask_3_6;
                    end
                    if (((stack_ptr_3 - 1) == 7)) begin
                        warp_pc_3 <= stack_pc_3_7;
                        warp_active_3 <= stack_mask_3_7;
                    end
                    stack_ptr_3 <= (stack_ptr_3 - 1);
                end else begin
                    if ((warp_active_3 == 0)) begin
                        warp_done_3 <= 1;
                    end
                end
            end
        end
    end

endmodule

module Scoreboard (
    input clk,
    input rst_n,
    input issue_valid,
    input [1:0] issue_warp,
    input [4:0] issue_dst,
    input [4:0] issue_src_a,
    input [4:0] issue_src_b,
    input [4:0] issue_src_c,
    input wb_valid,
    input [1:0] wb_warp,
    input [4:0] wb_dst,
    output issue_ready
);

    logic raw_hazard;
    reg entry_valid_0;
    reg entry_valid_1;
    reg entry_valid_2;
    reg entry_valid_3;
    reg entry_valid_4;
    reg entry_valid_5;
    reg entry_valid_6;
    reg entry_valid_7;
    reg entry_valid_8;
    reg entry_valid_9;
    reg entry_valid_10;
    reg entry_valid_11;
    reg entry_valid_12;
    reg entry_valid_13;
    reg entry_valid_14;
    reg entry_valid_15;
    reg entry_valid_16;
    reg entry_valid_17;
    reg entry_valid_18;
    reg entry_valid_19;
    reg entry_valid_20;
    reg entry_valid_21;
    reg entry_valid_22;
    reg entry_valid_23;
    reg entry_valid_24;
    reg entry_valid_25;
    reg entry_valid_26;
    reg entry_valid_27;
    reg entry_valid_28;
    reg entry_valid_29;
    reg entry_valid_30;
    reg entry_valid_31;
    reg [1:0] entry_warp_0;
    reg [1:0] entry_warp_1;
    reg [1:0] entry_warp_2;
    reg [1:0] entry_warp_3;
    reg [1:0] entry_warp_4;
    reg [1:0] entry_warp_5;
    reg [1:0] entry_warp_6;
    reg [1:0] entry_warp_7;
    reg [1:0] entry_warp_8;
    reg [1:0] entry_warp_9;
    reg [1:0] entry_warp_10;
    reg [1:0] entry_warp_11;
    reg [1:0] entry_warp_12;
    reg [1:0] entry_warp_13;
    reg [1:0] entry_warp_14;
    reg [1:0] entry_warp_15;
    reg [1:0] entry_warp_16;
    reg [1:0] entry_warp_17;
    reg [1:0] entry_warp_18;
    reg [1:0] entry_warp_19;
    reg [1:0] entry_warp_20;
    reg [1:0] entry_warp_21;
    reg [1:0] entry_warp_22;
    reg [1:0] entry_warp_23;
    reg [1:0] entry_warp_24;
    reg [1:0] entry_warp_25;
    reg [1:0] entry_warp_26;
    reg [1:0] entry_warp_27;
    reg [1:0] entry_warp_28;
    reg [1:0] entry_warp_29;
    reg [1:0] entry_warp_30;
    reg [1:0] entry_warp_31;
    reg [4:0] entry_reg_0;
    reg [4:0] entry_reg_1;
    reg [4:0] entry_reg_2;
    reg [4:0] entry_reg_3;
    reg [4:0] entry_reg_4;
    reg [4:0] entry_reg_5;
    reg [4:0] entry_reg_6;
    reg [4:0] entry_reg_7;
    reg [4:0] entry_reg_8;
    reg [4:0] entry_reg_9;
    reg [4:0] entry_reg_10;
    reg [4:0] entry_reg_11;
    reg [4:0] entry_reg_12;
    reg [4:0] entry_reg_13;
    reg [4:0] entry_reg_14;
    reg [4:0] entry_reg_15;
    reg [4:0] entry_reg_16;
    reg [4:0] entry_reg_17;
    reg [4:0] entry_reg_18;
    reg [4:0] entry_reg_19;
    reg [4:0] entry_reg_20;
    reg [4:0] entry_reg_21;
    reg [4:0] entry_reg_22;
    reg [4:0] entry_reg_23;
    reg [4:0] entry_reg_24;
    reg [4:0] entry_reg_25;
    reg [4:0] entry_reg_26;
    reg [4:0] entry_reg_27;
    reg [4:0] entry_reg_28;
    reg [4:0] entry_reg_29;
    reg [4:0] entry_reg_30;
    reg [4:0] entry_reg_31;

    assign issue_ready = (~raw_hazard);
    always @(*) begin
        if (entry_valid_0) begin
            if (((entry_warp_0 == issue_warp) & (((entry_reg_0 == issue_src_a) | (entry_reg_0 == issue_src_b)) | (entry_reg_0 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_1) begin
            if (((entry_warp_1 == issue_warp) & (((entry_reg_1 == issue_src_a) | (entry_reg_1 == issue_src_b)) | (entry_reg_1 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_2) begin
            if (((entry_warp_2 == issue_warp) & (((entry_reg_2 == issue_src_a) | (entry_reg_2 == issue_src_b)) | (entry_reg_2 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_3) begin
            if (((entry_warp_3 == issue_warp) & (((entry_reg_3 == issue_src_a) | (entry_reg_3 == issue_src_b)) | (entry_reg_3 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_4) begin
            if (((entry_warp_4 == issue_warp) & (((entry_reg_4 == issue_src_a) | (entry_reg_4 == issue_src_b)) | (entry_reg_4 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_5) begin
            if (((entry_warp_5 == issue_warp) & (((entry_reg_5 == issue_src_a) | (entry_reg_5 == issue_src_b)) | (entry_reg_5 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_6) begin
            if (((entry_warp_6 == issue_warp) & (((entry_reg_6 == issue_src_a) | (entry_reg_6 == issue_src_b)) | (entry_reg_6 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_7) begin
            if (((entry_warp_7 == issue_warp) & (((entry_reg_7 == issue_src_a) | (entry_reg_7 == issue_src_b)) | (entry_reg_7 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_8) begin
            if (((entry_warp_8 == issue_warp) & (((entry_reg_8 == issue_src_a) | (entry_reg_8 == issue_src_b)) | (entry_reg_8 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_9) begin
            if (((entry_warp_9 == issue_warp) & (((entry_reg_9 == issue_src_a) | (entry_reg_9 == issue_src_b)) | (entry_reg_9 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_10) begin
            if (((entry_warp_10 == issue_warp) & (((entry_reg_10 == issue_src_a) | (entry_reg_10 == issue_src_b)) | (entry_reg_10 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_11) begin
            if (((entry_warp_11 == issue_warp) & (((entry_reg_11 == issue_src_a) | (entry_reg_11 == issue_src_b)) | (entry_reg_11 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_12) begin
            if (((entry_warp_12 == issue_warp) & (((entry_reg_12 == issue_src_a) | (entry_reg_12 == issue_src_b)) | (entry_reg_12 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_13) begin
            if (((entry_warp_13 == issue_warp) & (((entry_reg_13 == issue_src_a) | (entry_reg_13 == issue_src_b)) | (entry_reg_13 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_14) begin
            if (((entry_warp_14 == issue_warp) & (((entry_reg_14 == issue_src_a) | (entry_reg_14 == issue_src_b)) | (entry_reg_14 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_15) begin
            if (((entry_warp_15 == issue_warp) & (((entry_reg_15 == issue_src_a) | (entry_reg_15 == issue_src_b)) | (entry_reg_15 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_16) begin
            if (((entry_warp_16 == issue_warp) & (((entry_reg_16 == issue_src_a) | (entry_reg_16 == issue_src_b)) | (entry_reg_16 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_17) begin
            if (((entry_warp_17 == issue_warp) & (((entry_reg_17 == issue_src_a) | (entry_reg_17 == issue_src_b)) | (entry_reg_17 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_18) begin
            if (((entry_warp_18 == issue_warp) & (((entry_reg_18 == issue_src_a) | (entry_reg_18 == issue_src_b)) | (entry_reg_18 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_19) begin
            if (((entry_warp_19 == issue_warp) & (((entry_reg_19 == issue_src_a) | (entry_reg_19 == issue_src_b)) | (entry_reg_19 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_20) begin
            if (((entry_warp_20 == issue_warp) & (((entry_reg_20 == issue_src_a) | (entry_reg_20 == issue_src_b)) | (entry_reg_20 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_21) begin
            if (((entry_warp_21 == issue_warp) & (((entry_reg_21 == issue_src_a) | (entry_reg_21 == issue_src_b)) | (entry_reg_21 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_22) begin
            if (((entry_warp_22 == issue_warp) & (((entry_reg_22 == issue_src_a) | (entry_reg_22 == issue_src_b)) | (entry_reg_22 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_23) begin
            if (((entry_warp_23 == issue_warp) & (((entry_reg_23 == issue_src_a) | (entry_reg_23 == issue_src_b)) | (entry_reg_23 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_24) begin
            if (((entry_warp_24 == issue_warp) & (((entry_reg_24 == issue_src_a) | (entry_reg_24 == issue_src_b)) | (entry_reg_24 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_25) begin
            if (((entry_warp_25 == issue_warp) & (((entry_reg_25 == issue_src_a) | (entry_reg_25 == issue_src_b)) | (entry_reg_25 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_26) begin
            if (((entry_warp_26 == issue_warp) & (((entry_reg_26 == issue_src_a) | (entry_reg_26 == issue_src_b)) | (entry_reg_26 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_27) begin
            if (((entry_warp_27 == issue_warp) & (((entry_reg_27 == issue_src_a) | (entry_reg_27 == issue_src_b)) | (entry_reg_27 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_28) begin
            if (((entry_warp_28 == issue_warp) & (((entry_reg_28 == issue_src_a) | (entry_reg_28 == issue_src_b)) | (entry_reg_28 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_29) begin
            if (((entry_warp_29 == issue_warp) & (((entry_reg_29 == issue_src_a) | (entry_reg_29 == issue_src_b)) | (entry_reg_29 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_30) begin
            if (((entry_warp_30 == issue_warp) & (((entry_reg_30 == issue_src_a) | (entry_reg_30 == issue_src_b)) | (entry_reg_30 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        if (entry_valid_31) begin
            if (((entry_warp_31 == issue_warp) & (((entry_reg_31 == issue_src_a) | (entry_reg_31 == issue_src_b)) | (entry_reg_31 == issue_src_c)))) begin
            end else begin
            end
        end else begin
        end
        raw_hazard = 1;
    end

    always @(posedge clk or negedge rst_n) begin
        if ((((wb_valid & entry_valid_0) & (entry_warp_0 == wb_warp)) & (entry_reg_0 == wb_dst))) begin
            entry_valid_0 <= 0;
        end
        if ((((wb_valid & entry_valid_1) & (entry_warp_1 == wb_warp)) & (entry_reg_1 == wb_dst))) begin
            entry_valid_1 <= 0;
        end
        if ((((wb_valid & entry_valid_2) & (entry_warp_2 == wb_warp)) & (entry_reg_2 == wb_dst))) begin
            entry_valid_2 <= 0;
        end
        if ((((wb_valid & entry_valid_3) & (entry_warp_3 == wb_warp)) & (entry_reg_3 == wb_dst))) begin
            entry_valid_3 <= 0;
        end
        if ((((wb_valid & entry_valid_4) & (entry_warp_4 == wb_warp)) & (entry_reg_4 == wb_dst))) begin
            entry_valid_4 <= 0;
        end
        if ((((wb_valid & entry_valid_5) & (entry_warp_5 == wb_warp)) & (entry_reg_5 == wb_dst))) begin
            entry_valid_5 <= 0;
        end
        if ((((wb_valid & entry_valid_6) & (entry_warp_6 == wb_warp)) & (entry_reg_6 == wb_dst))) begin
            entry_valid_6 <= 0;
        end
        if ((((wb_valid & entry_valid_7) & (entry_warp_7 == wb_warp)) & (entry_reg_7 == wb_dst))) begin
            entry_valid_7 <= 0;
        end
        if ((((wb_valid & entry_valid_8) & (entry_warp_8 == wb_warp)) & (entry_reg_8 == wb_dst))) begin
            entry_valid_8 <= 0;
        end
        if ((((wb_valid & entry_valid_9) & (entry_warp_9 == wb_warp)) & (entry_reg_9 == wb_dst))) begin
            entry_valid_9 <= 0;
        end
        if ((((wb_valid & entry_valid_10) & (entry_warp_10 == wb_warp)) & (entry_reg_10 == wb_dst))) begin
            entry_valid_10 <= 0;
        end
        if ((((wb_valid & entry_valid_11) & (entry_warp_11 == wb_warp)) & (entry_reg_11 == wb_dst))) begin
            entry_valid_11 <= 0;
        end
        if ((((wb_valid & entry_valid_12) & (entry_warp_12 == wb_warp)) & (entry_reg_12 == wb_dst))) begin
            entry_valid_12 <= 0;
        end
        if ((((wb_valid & entry_valid_13) & (entry_warp_13 == wb_warp)) & (entry_reg_13 == wb_dst))) begin
            entry_valid_13 <= 0;
        end
        if ((((wb_valid & entry_valid_14) & (entry_warp_14 == wb_warp)) & (entry_reg_14 == wb_dst))) begin
            entry_valid_14 <= 0;
        end
        if ((((wb_valid & entry_valid_15) & (entry_warp_15 == wb_warp)) & (entry_reg_15 == wb_dst))) begin
            entry_valid_15 <= 0;
        end
        if ((((wb_valid & entry_valid_16) & (entry_warp_16 == wb_warp)) & (entry_reg_16 == wb_dst))) begin
            entry_valid_16 <= 0;
        end
        if ((((wb_valid & entry_valid_17) & (entry_warp_17 == wb_warp)) & (entry_reg_17 == wb_dst))) begin
            entry_valid_17 <= 0;
        end
        if ((((wb_valid & entry_valid_18) & (entry_warp_18 == wb_warp)) & (entry_reg_18 == wb_dst))) begin
            entry_valid_18 <= 0;
        end
        if ((((wb_valid & entry_valid_19) & (entry_warp_19 == wb_warp)) & (entry_reg_19 == wb_dst))) begin
            entry_valid_19 <= 0;
        end
        if ((((wb_valid & entry_valid_20) & (entry_warp_20 == wb_warp)) & (entry_reg_20 == wb_dst))) begin
            entry_valid_20 <= 0;
        end
        if ((((wb_valid & entry_valid_21) & (entry_warp_21 == wb_warp)) & (entry_reg_21 == wb_dst))) begin
            entry_valid_21 <= 0;
        end
        if ((((wb_valid & entry_valid_22) & (entry_warp_22 == wb_warp)) & (entry_reg_22 == wb_dst))) begin
            entry_valid_22 <= 0;
        end
        if ((((wb_valid & entry_valid_23) & (entry_warp_23 == wb_warp)) & (entry_reg_23 == wb_dst))) begin
            entry_valid_23 <= 0;
        end
        if ((((wb_valid & entry_valid_24) & (entry_warp_24 == wb_warp)) & (entry_reg_24 == wb_dst))) begin
            entry_valid_24 <= 0;
        end
        if ((((wb_valid & entry_valid_25) & (entry_warp_25 == wb_warp)) & (entry_reg_25 == wb_dst))) begin
            entry_valid_25 <= 0;
        end
        if ((((wb_valid & entry_valid_26) & (entry_warp_26 == wb_warp)) & (entry_reg_26 == wb_dst))) begin
            entry_valid_26 <= 0;
        end
        if ((((wb_valid & entry_valid_27) & (entry_warp_27 == wb_warp)) & (entry_reg_27 == wb_dst))) begin
            entry_valid_27 <= 0;
        end
        if ((((wb_valid & entry_valid_28) & (entry_warp_28 == wb_warp)) & (entry_reg_28 == wb_dst))) begin
            entry_valid_28 <= 0;
        end
        if ((((wb_valid & entry_valid_29) & (entry_warp_29 == wb_warp)) & (entry_reg_29 == wb_dst))) begin
            entry_valid_29 <= 0;
        end
        if ((((wb_valid & entry_valid_30) & (entry_warp_30 == wb_warp)) & (entry_reg_30 == wb_dst))) begin
            entry_valid_30 <= 0;
        end
        if ((((wb_valid & entry_valid_31) & (entry_warp_31 == wb_warp)) & (entry_reg_31 == wb_dst))) begin
            entry_valid_31 <= 0;
        end
        if ((issue_valid & (~raw_hazard))) begin
            if ((-1 & (~entry_valid_0))) begin
                entry_valid_0 <= 1;
                entry_warp_0 <= issue_warp;
                entry_reg_0 <= issue_dst;
            end
            if ((-2 & (~entry_valid_1))) begin
                entry_valid_1 <= 1;
                entry_warp_1 <= issue_warp;
                entry_reg_1 <= issue_dst;
            end
            if ((-2 & (~entry_valid_2))) begin
                entry_valid_2 <= 1;
                entry_warp_2 <= issue_warp;
                entry_reg_2 <= issue_dst;
            end
            if ((-2 & (~entry_valid_3))) begin
                entry_valid_3 <= 1;
                entry_warp_3 <= issue_warp;
                entry_reg_3 <= issue_dst;
            end
            if ((-2 & (~entry_valid_4))) begin
                entry_valid_4 <= 1;
                entry_warp_4 <= issue_warp;
                entry_reg_4 <= issue_dst;
            end
            if ((-2 & (~entry_valid_5))) begin
                entry_valid_5 <= 1;
                entry_warp_5 <= issue_warp;
                entry_reg_5 <= issue_dst;
            end
            if ((-2 & (~entry_valid_6))) begin
                entry_valid_6 <= 1;
                entry_warp_6 <= issue_warp;
                entry_reg_6 <= issue_dst;
            end
            if ((-2 & (~entry_valid_7))) begin
                entry_valid_7 <= 1;
                entry_warp_7 <= issue_warp;
                entry_reg_7 <= issue_dst;
            end
            if ((-2 & (~entry_valid_8))) begin
                entry_valid_8 <= 1;
                entry_warp_8 <= issue_warp;
                entry_reg_8 <= issue_dst;
            end
            if ((-2 & (~entry_valid_9))) begin
                entry_valid_9 <= 1;
                entry_warp_9 <= issue_warp;
                entry_reg_9 <= issue_dst;
            end
            if ((-2 & (~entry_valid_10))) begin
                entry_valid_10 <= 1;
                entry_warp_10 <= issue_warp;
                entry_reg_10 <= issue_dst;
            end
            if ((-2 & (~entry_valid_11))) begin
                entry_valid_11 <= 1;
                entry_warp_11 <= issue_warp;
                entry_reg_11 <= issue_dst;
            end
            if ((-2 & (~entry_valid_12))) begin
                entry_valid_12 <= 1;
                entry_warp_12 <= issue_warp;
                entry_reg_12 <= issue_dst;
            end
            if ((-2 & (~entry_valid_13))) begin
                entry_valid_13 <= 1;
                entry_warp_13 <= issue_warp;
                entry_reg_13 <= issue_dst;
            end
            if ((-2 & (~entry_valid_14))) begin
                entry_valid_14 <= 1;
                entry_warp_14 <= issue_warp;
                entry_reg_14 <= issue_dst;
            end
            if ((-2 & (~entry_valid_15))) begin
                entry_valid_15 <= 1;
                entry_warp_15 <= issue_warp;
                entry_reg_15 <= issue_dst;
            end
            if ((-2 & (~entry_valid_16))) begin
                entry_valid_16 <= 1;
                entry_warp_16 <= issue_warp;
                entry_reg_16 <= issue_dst;
            end
            if ((-2 & (~entry_valid_17))) begin
                entry_valid_17 <= 1;
                entry_warp_17 <= issue_warp;
                entry_reg_17 <= issue_dst;
            end
            if ((-2 & (~entry_valid_18))) begin
                entry_valid_18 <= 1;
                entry_warp_18 <= issue_warp;
                entry_reg_18 <= issue_dst;
            end
            if ((-2 & (~entry_valid_19))) begin
                entry_valid_19 <= 1;
                entry_warp_19 <= issue_warp;
                entry_reg_19 <= issue_dst;
            end
            if ((-2 & (~entry_valid_20))) begin
                entry_valid_20 <= 1;
                entry_warp_20 <= issue_warp;
                entry_reg_20 <= issue_dst;
            end
            if ((-2 & (~entry_valid_21))) begin
                entry_valid_21 <= 1;
                entry_warp_21 <= issue_warp;
                entry_reg_21 <= issue_dst;
            end
            if ((-2 & (~entry_valid_22))) begin
                entry_valid_22 <= 1;
                entry_warp_22 <= issue_warp;
                entry_reg_22 <= issue_dst;
            end
            if ((-2 & (~entry_valid_23))) begin
                entry_valid_23 <= 1;
                entry_warp_23 <= issue_warp;
                entry_reg_23 <= issue_dst;
            end
            if ((-2 & (~entry_valid_24))) begin
                entry_valid_24 <= 1;
                entry_warp_24 <= issue_warp;
                entry_reg_24 <= issue_dst;
            end
            if ((-2 & (~entry_valid_25))) begin
                entry_valid_25 <= 1;
                entry_warp_25 <= issue_warp;
                entry_reg_25 <= issue_dst;
            end
            if ((-2 & (~entry_valid_26))) begin
                entry_valid_26 <= 1;
                entry_warp_26 <= issue_warp;
                entry_reg_26 <= issue_dst;
            end
            if ((-2 & (~entry_valid_27))) begin
                entry_valid_27 <= 1;
                entry_warp_27 <= issue_warp;
                entry_reg_27 <= issue_dst;
            end
            if ((-2 & (~entry_valid_28))) begin
                entry_valid_28 <= 1;
                entry_warp_28 <= issue_warp;
                entry_reg_28 <= issue_dst;
            end
            if ((-2 & (~entry_valid_29))) begin
                entry_valid_29 <= 1;
                entry_warp_29 <= issue_warp;
                entry_reg_29 <= issue_dst;
            end
            if ((-2 & (~entry_valid_30))) begin
                entry_valid_30 <= 1;
                entry_warp_30 <= issue_warp;
                entry_reg_30 <= issue_dst;
            end
            if ((-2 & (~entry_valid_31))) begin
                entry_valid_31 <= 1;
                entry_warp_31 <= issue_warp;
                entry_reg_31 <= issue_dst;
            end
        end
    end

endmodule

module Frontend (
    input clk,
    input rst_n,
    input fetch_valid,
    input [1:0] fetch_warp,
    input [15:0] fetch_pc,
    input imem_resp_valid,
    input [63:0] imem_resp_data,
    output fetch_ready,
    output reg imem_req_valid,
    output reg [15:0] imem_req_addr,
    output dec_valid,
    output [1:0] dec_warp,
    output [15:0] dec_pc,
    output [5:0] dec_opcode,
    output [5:0] dec_func,
    output [5:0] dec_dst,
    output [5:0] dec_src_a,
    output [5:0] dec_src_b,
    output [5:0] dec_src_c,
    output dec_pred_use,
    output [4:0] dec_pred_reg,
    output dec_pred_neg,
    output [2:0] dec_unit,
    output [17:0] dec_imm
);

    reg [63:0] icache_data [0:15];

    logic [7:0] cache_idx;
    logic [7:0] cache_tag;
    logic cache_hit;
    reg [7:0] icache_tag_0;
    reg [7:0] icache_tag_1;
    reg [7:0] icache_tag_2;
    reg [7:0] icache_tag_3;
    reg [7:0] icache_tag_4;
    reg [7:0] icache_tag_5;
    reg [7:0] icache_tag_6;
    reg [7:0] icache_tag_7;
    reg [7:0] icache_tag_8;
    reg [7:0] icache_tag_9;
    reg [7:0] icache_tag_10;
    reg [7:0] icache_tag_11;
    reg [7:0] icache_tag_12;
    reg [7:0] icache_tag_13;
    reg [7:0] icache_tag_14;
    reg [7:0] icache_tag_15;
    reg icache_valid_0;
    reg icache_valid_1;
    reg icache_valid_2;
    reg icache_valid_3;
    reg icache_valid_4;
    reg icache_valid_5;
    reg icache_valid_6;
    reg icache_valid_7;
    reg icache_valid_8;
    reg icache_valid_9;
    reg icache_valid_10;
    reg icache_valid_11;
    reg icache_valid_12;
    reg icache_valid_13;
    reg icache_valid_14;
    reg icache_valid_15;
    reg [1:0] state;
    reg [1:0] fetch_warp_r;
    reg [15:0] fetch_pc_r;
    reg [63:0] inst_r;

    assign dec_valid = (state == 3);
    assign dec_warp = fetch_warp_r;
    assign dec_pc = fetch_pc_r;
    assign fetch_ready = (state == 0);
    assign cache_idx = fetch_pc_r[7:0];
    assign cache_tag = (fetch_pc_r >> 8);
    assign cache_hit = (((cache_idx == 15) ? icache_valid_15 : ((cache_idx == 14) ? icache_valid_14 : ((cache_idx == 13) ? icache_valid_13 : ((cache_idx == 12) ? icache_valid_12 : ((cache_idx == 11) ? icache_valid_11 : ((cache_idx == 10) ? icache_valid_10 : ((cache_idx == 9) ? icache_valid_9 : ((cache_idx == 8) ? icache_valid_8 : ((cache_idx == 7) ? icache_valid_7 : ((cache_idx == 6) ? icache_valid_6 : ((cache_idx == 5) ? icache_valid_5 : ((cache_idx == 4) ? icache_valid_4 : ((cache_idx == 3) ? icache_valid_3 : ((cache_idx == 2) ? icache_valid_2 : ((cache_idx == 1) ? icache_valid_1 : icache_valid_0))))))))))))))) & (cache_tag == ((cache_idx == 15) ? icache_tag_15 : ((cache_idx == 14) ? icache_tag_14 : ((cache_idx == 13) ? icache_tag_13 : ((cache_idx == 12) ? icache_tag_12 : ((cache_idx == 11) ? icache_tag_11 : ((cache_idx == 10) ? icache_tag_10 : ((cache_idx == 9) ? icache_tag_9 : ((cache_idx == 8) ? icache_tag_8 : ((cache_idx == 7) ? icache_tag_7 : ((cache_idx == 6) ? icache_tag_6 : ((cache_idx == 5) ? icache_tag_5 : ((cache_idx == 4) ? icache_tag_4 : ((cache_idx == 3) ? icache_tag_3 : ((cache_idx == 2) ? icache_tag_2 : ((cache_idx == 1) ? icache_tag_1 : icache_tag_0)))))))))))))))));

    assign dec_opcode = ((inst_r >> 58) & 63);
    assign dec_func = ((inst_r >> 52) & 63);
    assign dec_dst = ((inst_r >> 46) & 63);
    assign dec_src_a = ((inst_r >> 40) & 63);
    assign dec_src_b = ((inst_r >> 34) & 63);
    assign dec_src_c = ((inst_r >> 28) & 63);
    assign dec_pred_use = ((inst_r >> 27) & 1);
    assign dec_pred_reg = ((inst_r >> 22) & 31);
    assign dec_pred_neg = ((inst_r >> 21) & 1);
    assign dec_unit = ((inst_r >> 18) & 7);
    assign dec_imm = ((((inst_r >> 10) & 255) << 10) | (inst_r & 1023));

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            state <= 0;
            fetch_warp_r <= 0;
            fetch_pc_r <= 0;
            icache_valid_0 <= 0;
            icache_valid_1 <= 0;
            icache_valid_2 <= 0;
            icache_valid_3 <= 0;
            icache_valid_4 <= 0;
            icache_valid_5 <= 0;
            icache_valid_6 <= 0;
            icache_valid_7 <= 0;
            icache_valid_8 <= 0;
            icache_valid_9 <= 0;
            icache_valid_10 <= 0;
            icache_valid_11 <= 0;
            icache_valid_12 <= 0;
            icache_valid_13 <= 0;
            icache_valid_14 <= 0;
            icache_valid_15 <= 0;
        end else begin
            if ((state == 0)) begin
                if (fetch_valid) begin
                    state <= 1;
                    fetch_warp_r <= fetch_warp;
                    fetch_pc_r <= fetch_pc;
                end
            end
            if ((state == 1)) begin
                if (cache_hit) begin
                    inst_r <= icache_data[cache_idx];
                    state <= 3;
                end else begin
                    state <= 2;
                    imem_req_valid <= 1;
                    imem_req_addr <= fetch_pc_r;
                end
            end
            if ((state == 2)) begin
                imem_req_valid <= 0;
                if (imem_resp_valid) begin
                    inst_r <= imem_resp_data;
                    icache_data[cache_idx] <= imem_resp_data;
                    if ((cache_idx == 0)) begin
                        icache_tag_0 <= cache_tag;
                        icache_valid_0 <= 1;
                    end
                    if ((cache_idx == 1)) begin
                        icache_tag_1 <= cache_tag;
                        icache_valid_1 <= 1;
                    end
                    if ((cache_idx == 2)) begin
                        icache_tag_2 <= cache_tag;
                        icache_valid_2 <= 1;
                    end
                    if ((cache_idx == 3)) begin
                        icache_tag_3 <= cache_tag;
                        icache_valid_3 <= 1;
                    end
                    if ((cache_idx == 4)) begin
                        icache_tag_4 <= cache_tag;
                        icache_valid_4 <= 1;
                    end
                    if ((cache_idx == 5)) begin
                        icache_tag_5 <= cache_tag;
                        icache_valid_5 <= 1;
                    end
                    if ((cache_idx == 6)) begin
                        icache_tag_6 <= cache_tag;
                        icache_valid_6 <= 1;
                    end
                    if ((cache_idx == 7)) begin
                        icache_tag_7 <= cache_tag;
                        icache_valid_7 <= 1;
                    end
                    if ((cache_idx == 8)) begin
                        icache_tag_8 <= cache_tag;
                        icache_valid_8 <= 1;
                    end
                    if ((cache_idx == 9)) begin
                        icache_tag_9 <= cache_tag;
                        icache_valid_9 <= 1;
                    end
                    if ((cache_idx == 10)) begin
                        icache_tag_10 <= cache_tag;
                        icache_valid_10 <= 1;
                    end
                    if ((cache_idx == 11)) begin
                        icache_tag_11 <= cache_tag;
                        icache_valid_11 <= 1;
                    end
                    if ((cache_idx == 12)) begin
                        icache_tag_12 <= cache_tag;
                        icache_valid_12 <= 1;
                    end
                    if ((cache_idx == 13)) begin
                        icache_tag_13 <= cache_tag;
                        icache_valid_13 <= 1;
                    end
                    if ((cache_idx == 14)) begin
                        icache_tag_14 <= cache_tag;
                        icache_valid_14 <= 1;
                    end
                    if ((cache_idx == 15)) begin
                        icache_tag_15 <= cache_tag;
                        icache_valid_15 <= 1;
                    end
                    state <= 3;
                end
            end
            if ((state == 3)) begin
                state <= 0;
            end
        end
    end

endmodule

module MemoryCoalescer (
    input clk,
    input rst_n,
    input req_valid,
    input req_is_store,
    input [31:0] req_addr_0,
    input [31:0] req_addr_1,
    input [31:0] req_addr_2,
    input [31:0] req_addr_3,
    input [31:0] req_addr_4,
    input [31:0] req_addr_5,
    input [31:0] req_addr_6,
    input [31:0] req_addr_7,
    input [31:0] req_addr_8,
    input [31:0] req_addr_9,
    input [31:0] req_addr_10,
    input [31:0] req_addr_11,
    input [31:0] req_addr_12,
    input [31:0] req_addr_13,
    input [31:0] req_addr_14,
    input [31:0] req_addr_15,
    input [31:0] req_addr_16,
    input [31:0] req_addr_17,
    input [31:0] req_addr_18,
    input [31:0] req_addr_19,
    input [31:0] req_addr_20,
    input [31:0] req_addr_21,
    input [31:0] req_addr_22,
    input [31:0] req_addr_23,
    input [31:0] req_addr_24,
    input [31:0] req_addr_25,
    input [31:0] req_addr_26,
    input [31:0] req_addr_27,
    input [31:0] req_addr_28,
    input [31:0] req_addr_29,
    input [31:0] req_addr_30,
    input [31:0] req_addr_31,
    input [31:0] req_data_0,
    input [31:0] req_data_1,
    input [31:0] req_data_2,
    input [31:0] req_data_3,
    input [31:0] req_data_4,
    input [31:0] req_data_5,
    input [31:0] req_data_6,
    input [31:0] req_data_7,
    input [31:0] req_data_8,
    input [31:0] req_data_9,
    input [31:0] req_data_10,
    input [31:0] req_data_11,
    input [31:0] req_data_12,
    input [31:0] req_data_13,
    input [31:0] req_data_14,
    input [31:0] req_data_15,
    input [31:0] req_data_16,
    input [31:0] req_data_17,
    input [31:0] req_data_18,
    input [31:0] req_data_19,
    input [31:0] req_data_20,
    input [31:0] req_data_21,
    input [31:0] req_data_22,
    input [31:0] req_data_23,
    input [31:0] req_data_24,
    input [31:0] req_data_25,
    input [31:0] req_data_26,
    input [31:0] req_data_27,
    input [31:0] req_data_28,
    input [31:0] req_data_29,
    input [31:0] req_data_30,
    input [31:0] req_data_31,
    input [31:0] req_mask,
    output out_valid,
    output out_is_store,
    output [31:0] out_addr,
    output [31:0] out_data_0,
    output [31:0] out_data_1,
    output [31:0] out_data_2,
    output [31:0] out_data_3,
    output [3:0] out_mask,
    output out_done
);

    logic [31:0] base_addr;
    logic [2:0] run_len;
    logic [3:0] run_mask;
    reg coal_state;
    reg [4:0] lane_ptr;

    assign out_valid = ((coal_state == 1) & (run_len > 0));
    assign out_is_store = req_is_store;
    assign out_addr = base_addr;
    assign out_mask = run_mask;
    assign out_done = ((coal_state == 1) & ((lane_ptr + run_len) >= 32));
    always @(*) begin
        if (((lane_ptr + 0) < 32)) begin
            out_data_0 = (((lane_ptr + 0) == 31) ? req_data_31 : (((lane_ptr + 0) == 30) ? req_data_30 : (((lane_ptr + 0) == 29) ? req_data_29 : (((lane_ptr + 0) == 28) ? req_data_28 : (((lane_ptr + 0) == 27) ? req_data_27 : (((lane_ptr + 0) == 26) ? req_data_26 : (((lane_ptr + 0) == 25) ? req_data_25 : (((lane_ptr + 0) == 24) ? req_data_24 : (((lane_ptr + 0) == 23) ? req_data_23 : (((lane_ptr + 0) == 22) ? req_data_22 : (((lane_ptr + 0) == 21) ? req_data_21 : (((lane_ptr + 0) == 20) ? req_data_20 : (((lane_ptr + 0) == 19) ? req_data_19 : (((lane_ptr + 0) == 18) ? req_data_18 : (((lane_ptr + 0) == 17) ? req_data_17 : (((lane_ptr + 0) == 16) ? req_data_16 : (((lane_ptr + 0) == 15) ? req_data_15 : (((lane_ptr + 0) == 14) ? req_data_14 : (((lane_ptr + 0) == 13) ? req_data_13 : (((lane_ptr + 0) == 12) ? req_data_12 : (((lane_ptr + 0) == 11) ? req_data_11 : (((lane_ptr + 0) == 10) ? req_data_10 : (((lane_ptr + 0) == 9) ? req_data_9 : (((lane_ptr + 0) == 8) ? req_data_8 : (((lane_ptr + 0) == 7) ? req_data_7 : (((lane_ptr + 0) == 6) ? req_data_6 : (((lane_ptr + 0) == 5) ? req_data_5 : (((lane_ptr + 0) == 4) ? req_data_4 : (((lane_ptr + 0) == 3) ? req_data_3 : (((lane_ptr + 0) == 2) ? req_data_2 : (((lane_ptr + 0) == 1) ? req_data_1 : req_data_0)))))))))))))))))))))))))))))));
        end else begin
            out_data_0 = 0;
        end
    end

    always @(*) begin
        if (((lane_ptr + 1) < 32)) begin
            out_data_1 = (((lane_ptr + 1) == 31) ? req_data_31 : (((lane_ptr + 1) == 30) ? req_data_30 : (((lane_ptr + 1) == 29) ? req_data_29 : (((lane_ptr + 1) == 28) ? req_data_28 : (((lane_ptr + 1) == 27) ? req_data_27 : (((lane_ptr + 1) == 26) ? req_data_26 : (((lane_ptr + 1) == 25) ? req_data_25 : (((lane_ptr + 1) == 24) ? req_data_24 : (((lane_ptr + 1) == 23) ? req_data_23 : (((lane_ptr + 1) == 22) ? req_data_22 : (((lane_ptr + 1) == 21) ? req_data_21 : (((lane_ptr + 1) == 20) ? req_data_20 : (((lane_ptr + 1) == 19) ? req_data_19 : (((lane_ptr + 1) == 18) ? req_data_18 : (((lane_ptr + 1) == 17) ? req_data_17 : (((lane_ptr + 1) == 16) ? req_data_16 : (((lane_ptr + 1) == 15) ? req_data_15 : (((lane_ptr + 1) == 14) ? req_data_14 : (((lane_ptr + 1) == 13) ? req_data_13 : (((lane_ptr + 1) == 12) ? req_data_12 : (((lane_ptr + 1) == 11) ? req_data_11 : (((lane_ptr + 1) == 10) ? req_data_10 : (((lane_ptr + 1) == 9) ? req_data_9 : (((lane_ptr + 1) == 8) ? req_data_8 : (((lane_ptr + 1) == 7) ? req_data_7 : (((lane_ptr + 1) == 6) ? req_data_6 : (((lane_ptr + 1) == 5) ? req_data_5 : (((lane_ptr + 1) == 4) ? req_data_4 : (((lane_ptr + 1) == 3) ? req_data_3 : (((lane_ptr + 1) == 2) ? req_data_2 : (((lane_ptr + 1) == 1) ? req_data_1 : req_data_0)))))))))))))))))))))))))))))));
        end else begin
            out_data_1 = 0;
        end
    end

    always @(*) begin
        if (((lane_ptr + 2) < 32)) begin
            out_data_2 = (((lane_ptr + 2) == 31) ? req_data_31 : (((lane_ptr + 2) == 30) ? req_data_30 : (((lane_ptr + 2) == 29) ? req_data_29 : (((lane_ptr + 2) == 28) ? req_data_28 : (((lane_ptr + 2) == 27) ? req_data_27 : (((lane_ptr + 2) == 26) ? req_data_26 : (((lane_ptr + 2) == 25) ? req_data_25 : (((lane_ptr + 2) == 24) ? req_data_24 : (((lane_ptr + 2) == 23) ? req_data_23 : (((lane_ptr + 2) == 22) ? req_data_22 : (((lane_ptr + 2) == 21) ? req_data_21 : (((lane_ptr + 2) == 20) ? req_data_20 : (((lane_ptr + 2) == 19) ? req_data_19 : (((lane_ptr + 2) == 18) ? req_data_18 : (((lane_ptr + 2) == 17) ? req_data_17 : (((lane_ptr + 2) == 16) ? req_data_16 : (((lane_ptr + 2) == 15) ? req_data_15 : (((lane_ptr + 2) == 14) ? req_data_14 : (((lane_ptr + 2) == 13) ? req_data_13 : (((lane_ptr + 2) == 12) ? req_data_12 : (((lane_ptr + 2) == 11) ? req_data_11 : (((lane_ptr + 2) == 10) ? req_data_10 : (((lane_ptr + 2) == 9) ? req_data_9 : (((lane_ptr + 2) == 8) ? req_data_8 : (((lane_ptr + 2) == 7) ? req_data_7 : (((lane_ptr + 2) == 6) ? req_data_6 : (((lane_ptr + 2) == 5) ? req_data_5 : (((lane_ptr + 2) == 4) ? req_data_4 : (((lane_ptr + 2) == 3) ? req_data_3 : (((lane_ptr + 2) == 2) ? req_data_2 : (((lane_ptr + 2) == 1) ? req_data_1 : req_data_0)))))))))))))))))))))))))))))));
        end else begin
            out_data_2 = 0;
        end
    end

    always @(*) begin
        if (((lane_ptr + 3) < 32)) begin
            out_data_3 = (((lane_ptr + 3) == 31) ? req_data_31 : (((lane_ptr + 3) == 30) ? req_data_30 : (((lane_ptr + 3) == 29) ? req_data_29 : (((lane_ptr + 3) == 28) ? req_data_28 : (((lane_ptr + 3) == 27) ? req_data_27 : (((lane_ptr + 3) == 26) ? req_data_26 : (((lane_ptr + 3) == 25) ? req_data_25 : (((lane_ptr + 3) == 24) ? req_data_24 : (((lane_ptr + 3) == 23) ? req_data_23 : (((lane_ptr + 3) == 22) ? req_data_22 : (((lane_ptr + 3) == 21) ? req_data_21 : (((lane_ptr + 3) == 20) ? req_data_20 : (((lane_ptr + 3) == 19) ? req_data_19 : (((lane_ptr + 3) == 18) ? req_data_18 : (((lane_ptr + 3) == 17) ? req_data_17 : (((lane_ptr + 3) == 16) ? req_data_16 : (((lane_ptr + 3) == 15) ? req_data_15 : (((lane_ptr + 3) == 14) ? req_data_14 : (((lane_ptr + 3) == 13) ? req_data_13 : (((lane_ptr + 3) == 12) ? req_data_12 : (((lane_ptr + 3) == 11) ? req_data_11 : (((lane_ptr + 3) == 10) ? req_data_10 : (((lane_ptr + 3) == 9) ? req_data_9 : (((lane_ptr + 3) == 8) ? req_data_8 : (((lane_ptr + 3) == 7) ? req_data_7 : (((lane_ptr + 3) == 6) ? req_data_6 : (((lane_ptr + 3) == 5) ? req_data_5 : (((lane_ptr + 3) == 4) ? req_data_4 : (((lane_ptr + 3) == 3) ? req_data_3 : (((lane_ptr + 3) == 2) ? req_data_2 : (((lane_ptr + 3) == 1) ? req_data_1 : req_data_0)))))))))))))))))))))))))))))));
        end else begin
            out_data_3 = 0;
        end
    end

    always @(*) begin
        base_addr = ((lane_ptr == 31) ? req_addr_31 : ((lane_ptr == 30) ? req_addr_30 : ((lane_ptr == 29) ? req_addr_29 : ((lane_ptr == 28) ? req_addr_28 : ((lane_ptr == 27) ? req_addr_27 : ((lane_ptr == 26) ? req_addr_26 : ((lane_ptr == 25) ? req_addr_25 : ((lane_ptr == 24) ? req_addr_24 : ((lane_ptr == 23) ? req_addr_23 : ((lane_ptr == 22) ? req_addr_22 : ((lane_ptr == 21) ? req_addr_21 : ((lane_ptr == 20) ? req_addr_20 : ((lane_ptr == 19) ? req_addr_19 : ((lane_ptr == 18) ? req_addr_18 : ((lane_ptr == 17) ? req_addr_17 : ((lane_ptr == 16) ? req_addr_16 : ((lane_ptr == 15) ? req_addr_15 : ((lane_ptr == 14) ? req_addr_14 : ((lane_ptr == 13) ? req_addr_13 : ((lane_ptr == 12) ? req_addr_12 : ((lane_ptr == 11) ? req_addr_11 : ((lane_ptr == 10) ? req_addr_10 : ((lane_ptr == 9) ? req_addr_9 : ((lane_ptr == 8) ? req_addr_8 : ((lane_ptr == 7) ? req_addr_7 : ((lane_ptr == 6) ? req_addr_6 : ((lane_ptr == 5) ? req_addr_5 : ((lane_ptr == 4) ? req_addr_4 : ((lane_ptr == 3) ? req_addr_3 : ((lane_ptr == 2) ? req_addr_2 : ((lane_ptr == 1) ? req_addr_1 : req_addr_0)))))))))))))))))))))))))))))));
        if (((lane_ptr + 0) < 32)) begin
            if ((((((lane_ptr + 0) == 31) ? req_addr_31 : (((lane_ptr + 0) == 30) ? req_addr_30 : (((lane_ptr + 0) == 29) ? req_addr_29 : (((lane_ptr + 0) == 28) ? req_addr_28 : (((lane_ptr + 0) == 27) ? req_addr_27 : (((lane_ptr + 0) == 26) ? req_addr_26 : (((lane_ptr + 0) == 25) ? req_addr_25 : (((lane_ptr + 0) == 24) ? req_addr_24 : (((lane_ptr + 0) == 23) ? req_addr_23 : (((lane_ptr + 0) == 22) ? req_addr_22 : (((lane_ptr + 0) == 21) ? req_addr_21 : (((lane_ptr + 0) == 20) ? req_addr_20 : (((lane_ptr + 0) == 19) ? req_addr_19 : (((lane_ptr + 0) == 18) ? req_addr_18 : (((lane_ptr + 0) == 17) ? req_addr_17 : (((lane_ptr + 0) == 16) ? req_addr_16 : (((lane_ptr + 0) == 15) ? req_addr_15 : (((lane_ptr + 0) == 14) ? req_addr_14 : (((lane_ptr + 0) == 13) ? req_addr_13 : (((lane_ptr + 0) == 12) ? req_addr_12 : (((lane_ptr + 0) == 11) ? req_addr_11 : (((lane_ptr + 0) == 10) ? req_addr_10 : (((lane_ptr + 0) == 9) ? req_addr_9 : (((lane_ptr + 0) == 8) ? req_addr_8 : (((lane_ptr + 0) == 7) ? req_addr_7 : (((lane_ptr + 0) == 6) ? req_addr_6 : (((lane_ptr + 0) == 5) ? req_addr_5 : (((lane_ptr + 0) == 4) ? req_addr_4 : (((lane_ptr + 0) == 3) ? req_addr_3 : (((lane_ptr + 0) == 2) ? req_addr_2 : (((lane_ptr + 0) == 1) ? req_addr_1 : req_addr_0))))))))))))))))))))))))))))))) == (((lane_ptr == 31) ? req_addr_31 : ((lane_ptr == 30) ? req_addr_30 : ((lane_ptr == 29) ? req_addr_29 : ((lane_ptr == 28) ? req_addr_28 : ((lane_ptr == 27) ? req_addr_27 : ((lane_ptr == 26) ? req_addr_26 : ((lane_ptr == 25) ? req_addr_25 : ((lane_ptr == 24) ? req_addr_24 : ((lane_ptr == 23) ? req_addr_23 : ((lane_ptr == 22) ? req_addr_22 : ((lane_ptr == 21) ? req_addr_21 : ((lane_ptr == 20) ? req_addr_20 : ((lane_ptr == 19) ? req_addr_19 : ((lane_ptr == 18) ? req_addr_18 : ((lane_ptr == 17) ? req_addr_17 : ((lane_ptr == 16) ? req_addr_16 : ((lane_ptr == 15) ? req_addr_15 : ((lane_ptr == 14) ? req_addr_14 : ((lane_ptr == 13) ? req_addr_13 : ((lane_ptr == 12) ? req_addr_12 : ((lane_ptr == 11) ? req_addr_11 : ((lane_ptr == 10) ? req_addr_10 : ((lane_ptr == 9) ? req_addr_9 : ((lane_ptr == 8) ? req_addr_8 : ((lane_ptr == 7) ? req_addr_7 : ((lane_ptr == 6) ? req_addr_6 : ((lane_ptr == 5) ? req_addr_5 : ((lane_ptr == 4) ? req_addr_4 : ((lane_ptr == 3) ? req_addr_3 : ((lane_ptr == 2) ? req_addr_2 : ((lane_ptr == 1) ? req_addr_1 : req_addr_0))))))))))))))))))))))))))))))) + 0)) & req_mask[(lane_ptr + 0)])) begin
            end else begin
            end
        end else begin
        end
        if (((lane_ptr + 1) < 32)) begin
            if ((((((lane_ptr + 1) == 31) ? req_addr_31 : (((lane_ptr + 1) == 30) ? req_addr_30 : (((lane_ptr + 1) == 29) ? req_addr_29 : (((lane_ptr + 1) == 28) ? req_addr_28 : (((lane_ptr + 1) == 27) ? req_addr_27 : (((lane_ptr + 1) == 26) ? req_addr_26 : (((lane_ptr + 1) == 25) ? req_addr_25 : (((lane_ptr + 1) == 24) ? req_addr_24 : (((lane_ptr + 1) == 23) ? req_addr_23 : (((lane_ptr + 1) == 22) ? req_addr_22 : (((lane_ptr + 1) == 21) ? req_addr_21 : (((lane_ptr + 1) == 20) ? req_addr_20 : (((lane_ptr + 1) == 19) ? req_addr_19 : (((lane_ptr + 1) == 18) ? req_addr_18 : (((lane_ptr + 1) == 17) ? req_addr_17 : (((lane_ptr + 1) == 16) ? req_addr_16 : (((lane_ptr + 1) == 15) ? req_addr_15 : (((lane_ptr + 1) == 14) ? req_addr_14 : (((lane_ptr + 1) == 13) ? req_addr_13 : (((lane_ptr + 1) == 12) ? req_addr_12 : (((lane_ptr + 1) == 11) ? req_addr_11 : (((lane_ptr + 1) == 10) ? req_addr_10 : (((lane_ptr + 1) == 9) ? req_addr_9 : (((lane_ptr + 1) == 8) ? req_addr_8 : (((lane_ptr + 1) == 7) ? req_addr_7 : (((lane_ptr + 1) == 6) ? req_addr_6 : (((lane_ptr + 1) == 5) ? req_addr_5 : (((lane_ptr + 1) == 4) ? req_addr_4 : (((lane_ptr + 1) == 3) ? req_addr_3 : (((lane_ptr + 1) == 2) ? req_addr_2 : (((lane_ptr + 1) == 1) ? req_addr_1 : req_addr_0))))))))))))))))))))))))))))))) == (((lane_ptr == 31) ? req_addr_31 : ((lane_ptr == 30) ? req_addr_30 : ((lane_ptr == 29) ? req_addr_29 : ((lane_ptr == 28) ? req_addr_28 : ((lane_ptr == 27) ? req_addr_27 : ((lane_ptr == 26) ? req_addr_26 : ((lane_ptr == 25) ? req_addr_25 : ((lane_ptr == 24) ? req_addr_24 : ((lane_ptr == 23) ? req_addr_23 : ((lane_ptr == 22) ? req_addr_22 : ((lane_ptr == 21) ? req_addr_21 : ((lane_ptr == 20) ? req_addr_20 : ((lane_ptr == 19) ? req_addr_19 : ((lane_ptr == 18) ? req_addr_18 : ((lane_ptr == 17) ? req_addr_17 : ((lane_ptr == 16) ? req_addr_16 : ((lane_ptr == 15) ? req_addr_15 : ((lane_ptr == 14) ? req_addr_14 : ((lane_ptr == 13) ? req_addr_13 : ((lane_ptr == 12) ? req_addr_12 : ((lane_ptr == 11) ? req_addr_11 : ((lane_ptr == 10) ? req_addr_10 : ((lane_ptr == 9) ? req_addr_9 : ((lane_ptr == 8) ? req_addr_8 : ((lane_ptr == 7) ? req_addr_7 : ((lane_ptr == 6) ? req_addr_6 : ((lane_ptr == 5) ? req_addr_5 : ((lane_ptr == 4) ? req_addr_4 : ((lane_ptr == 3) ? req_addr_3 : ((lane_ptr == 2) ? req_addr_2 : ((lane_ptr == 1) ? req_addr_1 : req_addr_0))))))))))))))))))))))))))))))) + 4)) & req_mask[(lane_ptr + 1)])) begin
            end else begin
            end
        end else begin
        end
        if (((lane_ptr + 2) < 32)) begin
            if ((((((lane_ptr + 2) == 31) ? req_addr_31 : (((lane_ptr + 2) == 30) ? req_addr_30 : (((lane_ptr + 2) == 29) ? req_addr_29 : (((lane_ptr + 2) == 28) ? req_addr_28 : (((lane_ptr + 2) == 27) ? req_addr_27 : (((lane_ptr + 2) == 26) ? req_addr_26 : (((lane_ptr + 2) == 25) ? req_addr_25 : (((lane_ptr + 2) == 24) ? req_addr_24 : (((lane_ptr + 2) == 23) ? req_addr_23 : (((lane_ptr + 2) == 22) ? req_addr_22 : (((lane_ptr + 2) == 21) ? req_addr_21 : (((lane_ptr + 2) == 20) ? req_addr_20 : (((lane_ptr + 2) == 19) ? req_addr_19 : (((lane_ptr + 2) == 18) ? req_addr_18 : (((lane_ptr + 2) == 17) ? req_addr_17 : (((lane_ptr + 2) == 16) ? req_addr_16 : (((lane_ptr + 2) == 15) ? req_addr_15 : (((lane_ptr + 2) == 14) ? req_addr_14 : (((lane_ptr + 2) == 13) ? req_addr_13 : (((lane_ptr + 2) == 12) ? req_addr_12 : (((lane_ptr + 2) == 11) ? req_addr_11 : (((lane_ptr + 2) == 10) ? req_addr_10 : (((lane_ptr + 2) == 9) ? req_addr_9 : (((lane_ptr + 2) == 8) ? req_addr_8 : (((lane_ptr + 2) == 7) ? req_addr_7 : (((lane_ptr + 2) == 6) ? req_addr_6 : (((lane_ptr + 2) == 5) ? req_addr_5 : (((lane_ptr + 2) == 4) ? req_addr_4 : (((lane_ptr + 2) == 3) ? req_addr_3 : (((lane_ptr + 2) == 2) ? req_addr_2 : (((lane_ptr + 2) == 1) ? req_addr_1 : req_addr_0))))))))))))))))))))))))))))))) == (((lane_ptr == 31) ? req_addr_31 : ((lane_ptr == 30) ? req_addr_30 : ((lane_ptr == 29) ? req_addr_29 : ((lane_ptr == 28) ? req_addr_28 : ((lane_ptr == 27) ? req_addr_27 : ((lane_ptr == 26) ? req_addr_26 : ((lane_ptr == 25) ? req_addr_25 : ((lane_ptr == 24) ? req_addr_24 : ((lane_ptr == 23) ? req_addr_23 : ((lane_ptr == 22) ? req_addr_22 : ((lane_ptr == 21) ? req_addr_21 : ((lane_ptr == 20) ? req_addr_20 : ((lane_ptr == 19) ? req_addr_19 : ((lane_ptr == 18) ? req_addr_18 : ((lane_ptr == 17) ? req_addr_17 : ((lane_ptr == 16) ? req_addr_16 : ((lane_ptr == 15) ? req_addr_15 : ((lane_ptr == 14) ? req_addr_14 : ((lane_ptr == 13) ? req_addr_13 : ((lane_ptr == 12) ? req_addr_12 : ((lane_ptr == 11) ? req_addr_11 : ((lane_ptr == 10) ? req_addr_10 : ((lane_ptr == 9) ? req_addr_9 : ((lane_ptr == 8) ? req_addr_8 : ((lane_ptr == 7) ? req_addr_7 : ((lane_ptr == 6) ? req_addr_6 : ((lane_ptr == 5) ? req_addr_5 : ((lane_ptr == 4) ? req_addr_4 : ((lane_ptr == 3) ? req_addr_3 : ((lane_ptr == 2) ? req_addr_2 : ((lane_ptr == 1) ? req_addr_1 : req_addr_0))))))))))))))))))))))))))))))) + 8)) & req_mask[(lane_ptr + 2)])) begin
            end else begin
            end
        end else begin
        end
        if (((lane_ptr + 3) < 32)) begin
            if ((((((lane_ptr + 3) == 31) ? req_addr_31 : (((lane_ptr + 3) == 30) ? req_addr_30 : (((lane_ptr + 3) == 29) ? req_addr_29 : (((lane_ptr + 3) == 28) ? req_addr_28 : (((lane_ptr + 3) == 27) ? req_addr_27 : (((lane_ptr + 3) == 26) ? req_addr_26 : (((lane_ptr + 3) == 25) ? req_addr_25 : (((lane_ptr + 3) == 24) ? req_addr_24 : (((lane_ptr + 3) == 23) ? req_addr_23 : (((lane_ptr + 3) == 22) ? req_addr_22 : (((lane_ptr + 3) == 21) ? req_addr_21 : (((lane_ptr + 3) == 20) ? req_addr_20 : (((lane_ptr + 3) == 19) ? req_addr_19 : (((lane_ptr + 3) == 18) ? req_addr_18 : (((lane_ptr + 3) == 17) ? req_addr_17 : (((lane_ptr + 3) == 16) ? req_addr_16 : (((lane_ptr + 3) == 15) ? req_addr_15 : (((lane_ptr + 3) == 14) ? req_addr_14 : (((lane_ptr + 3) == 13) ? req_addr_13 : (((lane_ptr + 3) == 12) ? req_addr_12 : (((lane_ptr + 3) == 11) ? req_addr_11 : (((lane_ptr + 3) == 10) ? req_addr_10 : (((lane_ptr + 3) == 9) ? req_addr_9 : (((lane_ptr + 3) == 8) ? req_addr_8 : (((lane_ptr + 3) == 7) ? req_addr_7 : (((lane_ptr + 3) == 6) ? req_addr_6 : (((lane_ptr + 3) == 5) ? req_addr_5 : (((lane_ptr + 3) == 4) ? req_addr_4 : (((lane_ptr + 3) == 3) ? req_addr_3 : (((lane_ptr + 3) == 2) ? req_addr_2 : (((lane_ptr + 3) == 1) ? req_addr_1 : req_addr_0))))))))))))))))))))))))))))))) == (((lane_ptr == 31) ? req_addr_31 : ((lane_ptr == 30) ? req_addr_30 : ((lane_ptr == 29) ? req_addr_29 : ((lane_ptr == 28) ? req_addr_28 : ((lane_ptr == 27) ? req_addr_27 : ((lane_ptr == 26) ? req_addr_26 : ((lane_ptr == 25) ? req_addr_25 : ((lane_ptr == 24) ? req_addr_24 : ((lane_ptr == 23) ? req_addr_23 : ((lane_ptr == 22) ? req_addr_22 : ((lane_ptr == 21) ? req_addr_21 : ((lane_ptr == 20) ? req_addr_20 : ((lane_ptr == 19) ? req_addr_19 : ((lane_ptr == 18) ? req_addr_18 : ((lane_ptr == 17) ? req_addr_17 : ((lane_ptr == 16) ? req_addr_16 : ((lane_ptr == 15) ? req_addr_15 : ((lane_ptr == 14) ? req_addr_14 : ((lane_ptr == 13) ? req_addr_13 : ((lane_ptr == 12) ? req_addr_12 : ((lane_ptr == 11) ? req_addr_11 : ((lane_ptr == 10) ? req_addr_10 : ((lane_ptr == 9) ? req_addr_9 : ((lane_ptr == 8) ? req_addr_8 : ((lane_ptr == 7) ? req_addr_7 : ((lane_ptr == 6) ? req_addr_6 : ((lane_ptr == 5) ? req_addr_5 : ((lane_ptr == 4) ? req_addr_4 : ((lane_ptr == 3) ? req_addr_3 : ((lane_ptr == 2) ? req_addr_2 : ((lane_ptr == 1) ? req_addr_1 : req_addr_0))))))))))))))))))))))))))))))) + 12)) & req_mask[(lane_ptr + 3)])) begin
            end else begin
            end
        end else begin
        end
        run_len = 4;
        run_mask = 15;
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            coal_state <= 0;
            lane_ptr <= 0;
        end else begin
            if ((coal_state == 0)) begin
                if (req_valid) begin
                    coal_state <= 1;
                    lane_ptr <= 0;
                end
            end else begin
                if (((lane_ptr + run_len) >= 32)) begin
                    coal_state <= 0;
                    lane_ptr <= 0;
                end else begin
                    lane_ptr <= (lane_ptr + run_len);
                end
            end
        end
    end

endmodule

module L1Cache (
    input clk,
    input rst_n,
    input req_valid,
    input req_is_store,
    input [31:0] req_addr,
    input [31:0] req_data,
    input [3:0] req_mask,
    input fill_valid,
    input [31:0] fill_addr,
    input [31:0] fill_data_0,
    input [31:0] fill_data_1,
    input [31:0] fill_data_2,
    input [31:0] fill_data_3,
    input [31:0] fill_data_4,
    input [31:0] fill_data_5,
    input [31:0] fill_data_6,
    input [31:0] fill_data_7,
    input [31:0] fill_data_8,
    input [31:0] fill_data_9,
    input [31:0] fill_data_10,
    input [31:0] fill_data_11,
    input [31:0] fill_data_12,
    input [31:0] fill_data_13,
    input [31:0] fill_data_14,
    input [31:0] fill_data_15,
    input [31:0] fill_data_16,
    input [31:0] fill_data_17,
    input [31:0] fill_data_18,
    input [31:0] fill_data_19,
    input [31:0] fill_data_20,
    input [31:0] fill_data_21,
    input [31:0] fill_data_22,
    input [31:0] fill_data_23,
    input [31:0] fill_data_24,
    input [31:0] fill_data_25,
    input [31:0] fill_data_26,
    input [31:0] fill_data_27,
    input [31:0] fill_data_28,
    input [31:0] fill_data_29,
    input [31:0] fill_data_30,
    input [31:0] fill_data_31,
    output resp_valid,
    output [31:0] resp_data,
    output resp_miss,
    output reg miss_valid,
    output reg [31:0] miss_addr
);

    reg [31:0] data_s0_w0 [0:31];
    reg [31:0] data_s0_w1 [0:31];
    reg [31:0] data_s0_w2 [0:31];
    reg [31:0] data_s0_w3 [0:31];
    reg [31:0] data_s1_w0 [0:31];
    reg [31:0] data_s1_w1 [0:31];
    reg [31:0] data_s1_w2 [0:31];
    reg [31:0] data_s1_w3 [0:31];
    reg [31:0] data_s2_w0 [0:31];
    reg [31:0] data_s2_w1 [0:31];
    reg [31:0] data_s2_w2 [0:31];
    reg [31:0] data_s2_w3 [0:31];
    reg [31:0] data_s3_w0 [0:31];
    reg [31:0] data_s3_w1 [0:31];
    reg [31:0] data_s3_w2 [0:31];
    reg [31:0] data_s3_w3 [0:31];
    reg [31:0] data_s4_w0 [0:31];
    reg [31:0] data_s4_w1 [0:31];
    reg [31:0] data_s4_w2 [0:31];
    reg [31:0] data_s4_w3 [0:31];
    reg [31:0] data_s5_w0 [0:31];
    reg [31:0] data_s5_w1 [0:31];
    reg [31:0] data_s5_w2 [0:31];
    reg [31:0] data_s5_w3 [0:31];
    reg [31:0] data_s6_w0 [0:31];
    reg [31:0] data_s6_w1 [0:31];
    reg [31:0] data_s6_w2 [0:31];
    reg [31:0] data_s6_w3 [0:31];
    reg [31:0] data_s7_w0 [0:31];
    reg [31:0] data_s7_w1 [0:31];
    reg [31:0] data_s7_w2 [0:31];
    reg [31:0] data_s7_w3 [0:31];
    reg [31:0] data_s8_w0 [0:31];
    reg [31:0] data_s8_w1 [0:31];
    reg [31:0] data_s8_w2 [0:31];
    reg [31:0] data_s8_w3 [0:31];
    reg [31:0] data_s9_w0 [0:31];
    reg [31:0] data_s9_w1 [0:31];
    reg [31:0] data_s9_w2 [0:31];
    reg [31:0] data_s9_w3 [0:31];
    reg [31:0] data_s10_w0 [0:31];
    reg [31:0] data_s10_w1 [0:31];
    reg [31:0] data_s10_w2 [0:31];
    reg [31:0] data_s10_w3 [0:31];
    reg [31:0] data_s11_w0 [0:31];
    reg [31:0] data_s11_w1 [0:31];
    reg [31:0] data_s11_w2 [0:31];
    reg [31:0] data_s11_w3 [0:31];
    reg [31:0] data_s12_w0 [0:31];
    reg [31:0] data_s12_w1 [0:31];
    reg [31:0] data_s12_w2 [0:31];
    reg [31:0] data_s12_w3 [0:31];
    reg [31:0] data_s13_w0 [0:31];
    reg [31:0] data_s13_w1 [0:31];
    reg [31:0] data_s13_w2 [0:31];
    reg [31:0] data_s13_w3 [0:31];
    reg [31:0] data_s14_w0 [0:31];
    reg [31:0] data_s14_w1 [0:31];
    reg [31:0] data_s14_w2 [0:31];
    reg [31:0] data_s14_w3 [0:31];
    reg [31:0] data_s15_w0 [0:31];
    reg [31:0] data_s15_w1 [0:31];
    reg [31:0] data_s15_w2 [0:31];
    reg [31:0] data_s15_w3 [0:31];

    logic [3:0] req_set;
    logic [20:0] req_tag;
    logic [6:0] req_offset;
    logic hit;
    logic [1:0] hit_way;
    logic [31:0] hit_data;
    reg [1:0] state;

    assign resp_valid = ((req_valid & hit) & (state == 0));
    assign resp_data = hit_data;
    assign resp_miss = ((req_valid & (~hit)) & (state == 0));
    assign req_offset = req_addr[6:0];
    assign req_set = ((req_addr >> 7) & 15);
    assign req_tag = (req_addr >> 11);

    always @(*) begin
        if ((((req_set == 0) & valid_s0_w0) & (tag_s0_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 0) & valid_s0_w1) & (tag_s0_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 0) & valid_s0_w2) & (tag_s0_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 0) & valid_s0_w3) & (tag_s0_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 1) & valid_s1_w0) & (tag_s1_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 1) & valid_s1_w1) & (tag_s1_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 1) & valid_s1_w2) & (tag_s1_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 1) & valid_s1_w3) & (tag_s1_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 2) & valid_s2_w0) & (tag_s2_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 2) & valid_s2_w1) & (tag_s2_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 2) & valid_s2_w2) & (tag_s2_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 2) & valid_s2_w3) & (tag_s2_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 3) & valid_s3_w0) & (tag_s3_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 3) & valid_s3_w1) & (tag_s3_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 3) & valid_s3_w2) & (tag_s3_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 3) & valid_s3_w3) & (tag_s3_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 4) & valid_s4_w0) & (tag_s4_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 4) & valid_s4_w1) & (tag_s4_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 4) & valid_s4_w2) & (tag_s4_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 4) & valid_s4_w3) & (tag_s4_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 5) & valid_s5_w0) & (tag_s5_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 5) & valid_s5_w1) & (tag_s5_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 5) & valid_s5_w2) & (tag_s5_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 5) & valid_s5_w3) & (tag_s5_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 6) & valid_s6_w0) & (tag_s6_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 6) & valid_s6_w1) & (tag_s6_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 6) & valid_s6_w2) & (tag_s6_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 6) & valid_s6_w3) & (tag_s6_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 7) & valid_s7_w0) & (tag_s7_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 7) & valid_s7_w1) & (tag_s7_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 7) & valid_s7_w2) & (tag_s7_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 7) & valid_s7_w3) & (tag_s7_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 8) & valid_s8_w0) & (tag_s8_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 8) & valid_s8_w1) & (tag_s8_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 8) & valid_s8_w2) & (tag_s8_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 8) & valid_s8_w3) & (tag_s8_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 9) & valid_s9_w0) & (tag_s9_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 9) & valid_s9_w1) & (tag_s9_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 9) & valid_s9_w2) & (tag_s9_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 9) & valid_s9_w3) & (tag_s9_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 10) & valid_s10_w0) & (tag_s10_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 10) & valid_s10_w1) & (tag_s10_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 10) & valid_s10_w2) & (tag_s10_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 10) & valid_s10_w3) & (tag_s10_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 11) & valid_s11_w0) & (tag_s11_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 11) & valid_s11_w1) & (tag_s11_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 11) & valid_s11_w2) & (tag_s11_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 11) & valid_s11_w3) & (tag_s11_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 12) & valid_s12_w0) & (tag_s12_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 12) & valid_s12_w1) & (tag_s12_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 12) & valid_s12_w2) & (tag_s12_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 12) & valid_s12_w3) & (tag_s12_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 13) & valid_s13_w0) & (tag_s13_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 13) & valid_s13_w1) & (tag_s13_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 13) & valid_s13_w2) & (tag_s13_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 13) & valid_s13_w3) & (tag_s13_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 14) & valid_s14_w0) & (tag_s14_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 14) & valid_s14_w1) & (tag_s14_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 14) & valid_s14_w2) & (tag_s14_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 14) & valid_s14_w3) & (tag_s14_w3 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 15) & valid_s15_w0) & (tag_s15_w0 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 15) & valid_s15_w1) & (tag_s15_w1 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 15) & valid_s15_w2) & (tag_s15_w2 == req_tag))) begin
        end else begin
        end
        if ((((req_set == 15) & valid_s15_w3) & (tag_s15_w3 == req_tag))) begin
        end else begin
        end
        hit = 1;
        hit_way = 3;
        hit_data = data_s15_w3[req_offset];
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            state <= 0;
            valid_s0_w0 <= 0;
            valid_s0_w1 <= 0;
            valid_s0_w2 <= 0;
            valid_s0_w3 <= 0;
            valid_s1_w0 <= 0;
            valid_s1_w1 <= 0;
            valid_s1_w2 <= 0;
            valid_s1_w3 <= 0;
            valid_s2_w0 <= 0;
            valid_s2_w1 <= 0;
            valid_s2_w2 <= 0;
            valid_s2_w3 <= 0;
            valid_s3_w0 <= 0;
            valid_s3_w1 <= 0;
            valid_s3_w2 <= 0;
            valid_s3_w3 <= 0;
            valid_s4_w0 <= 0;
            valid_s4_w1 <= 0;
            valid_s4_w2 <= 0;
            valid_s4_w3 <= 0;
            valid_s5_w0 <= 0;
            valid_s5_w1 <= 0;
            valid_s5_w2 <= 0;
            valid_s5_w3 <= 0;
            valid_s6_w0 <= 0;
            valid_s6_w1 <= 0;
            valid_s6_w2 <= 0;
            valid_s6_w3 <= 0;
            valid_s7_w0 <= 0;
            valid_s7_w1 <= 0;
            valid_s7_w2 <= 0;
            valid_s7_w3 <= 0;
            valid_s8_w0 <= 0;
            valid_s8_w1 <= 0;
            valid_s8_w2 <= 0;
            valid_s8_w3 <= 0;
            valid_s9_w0 <= 0;
            valid_s9_w1 <= 0;
            valid_s9_w2 <= 0;
            valid_s9_w3 <= 0;
            valid_s10_w0 <= 0;
            valid_s10_w1 <= 0;
            valid_s10_w2 <= 0;
            valid_s10_w3 <= 0;
            valid_s11_w0 <= 0;
            valid_s11_w1 <= 0;
            valid_s11_w2 <= 0;
            valid_s11_w3 <= 0;
            valid_s12_w0 <= 0;
            valid_s12_w1 <= 0;
            valid_s12_w2 <= 0;
            valid_s12_w3 <= 0;
            valid_s13_w0 <= 0;
            valid_s13_w1 <= 0;
            valid_s13_w2 <= 0;
            valid_s13_w3 <= 0;
            valid_s14_w0 <= 0;
            valid_s14_w1 <= 0;
            valid_s14_w2 <= 0;
            valid_s14_w3 <= 0;
            valid_s15_w0 <= 0;
            valid_s15_w1 <= 0;
            valid_s15_w2 <= 0;
            valid_s15_w3 <= 0;
        end else begin
            if ((state == 0)) begin
                if (req_valid) begin
                    if (hit) begin
                        state <= 0;
                    end else begin
                        state <= 1;
                    end
                end
            end
            if ((state == 1)) begin
                miss_valid <= 1;
                miss_addr <= req_addr;
                if (fill_valid) begin
                    miss_valid <= 0;
                    state <= 2;
                end
            end
            if ((state == 2)) begin
                if ((req_set == 0)) begin
                    valid_s0_w0 <= 1;
                    tag_s0_w0 <= req_tag;
                    data_s0_w0[0] <= fill_data_0;
                    data_s0_w0[1] <= fill_data_1;
                    data_s0_w0[2] <= fill_data_2;
                    data_s0_w0[3] <= fill_data_3;
                    data_s0_w0[4] <= fill_data_4;
                    data_s0_w0[5] <= fill_data_5;
                    data_s0_w0[6] <= fill_data_6;
                    data_s0_w0[7] <= fill_data_7;
                    data_s0_w0[8] <= fill_data_8;
                    data_s0_w0[9] <= fill_data_9;
                    data_s0_w0[10] <= fill_data_10;
                    data_s0_w0[11] <= fill_data_11;
                    data_s0_w0[12] <= fill_data_12;
                    data_s0_w0[13] <= fill_data_13;
                    data_s0_w0[14] <= fill_data_14;
                    data_s0_w0[15] <= fill_data_15;
                    data_s0_w0[16] <= fill_data_16;
                    data_s0_w0[17] <= fill_data_17;
                    data_s0_w0[18] <= fill_data_18;
                    data_s0_w0[19] <= fill_data_19;
                    data_s0_w0[20] <= fill_data_20;
                    data_s0_w0[21] <= fill_data_21;
                    data_s0_w0[22] <= fill_data_22;
                    data_s0_w0[23] <= fill_data_23;
                    data_s0_w0[24] <= fill_data_24;
                    data_s0_w0[25] <= fill_data_25;
                    data_s0_w0[26] <= fill_data_26;
                    data_s0_w0[27] <= fill_data_27;
                    data_s0_w0[28] <= fill_data_28;
                    data_s0_w0[29] <= fill_data_29;
                    data_s0_w0[30] <= fill_data_30;
                    data_s0_w0[31] <= fill_data_31;
                end
                if ((req_set == 1)) begin
                    valid_s1_w0 <= 1;
                    tag_s1_w0 <= req_tag;
                    data_s1_w0[0] <= fill_data_0;
                    data_s1_w0[1] <= fill_data_1;
                    data_s1_w0[2] <= fill_data_2;
                    data_s1_w0[3] <= fill_data_3;
                    data_s1_w0[4] <= fill_data_4;
                    data_s1_w0[5] <= fill_data_5;
                    data_s1_w0[6] <= fill_data_6;
                    data_s1_w0[7] <= fill_data_7;
                    data_s1_w0[8] <= fill_data_8;
                    data_s1_w0[9] <= fill_data_9;
                    data_s1_w0[10] <= fill_data_10;
                    data_s1_w0[11] <= fill_data_11;
                    data_s1_w0[12] <= fill_data_12;
                    data_s1_w0[13] <= fill_data_13;
                    data_s1_w0[14] <= fill_data_14;
                    data_s1_w0[15] <= fill_data_15;
                    data_s1_w0[16] <= fill_data_16;
                    data_s1_w0[17] <= fill_data_17;
                    data_s1_w0[18] <= fill_data_18;
                    data_s1_w0[19] <= fill_data_19;
                    data_s1_w0[20] <= fill_data_20;
                    data_s1_w0[21] <= fill_data_21;
                    data_s1_w0[22] <= fill_data_22;
                    data_s1_w0[23] <= fill_data_23;
                    data_s1_w0[24] <= fill_data_24;
                    data_s1_w0[25] <= fill_data_25;
                    data_s1_w0[26] <= fill_data_26;
                    data_s1_w0[27] <= fill_data_27;
                    data_s1_w0[28] <= fill_data_28;
                    data_s1_w0[29] <= fill_data_29;
                    data_s1_w0[30] <= fill_data_30;
                    data_s1_w0[31] <= fill_data_31;
                end
                if ((req_set == 2)) begin
                    valid_s2_w0 <= 1;
                    tag_s2_w0 <= req_tag;
                    data_s2_w0[0] <= fill_data_0;
                    data_s2_w0[1] <= fill_data_1;
                    data_s2_w0[2] <= fill_data_2;
                    data_s2_w0[3] <= fill_data_3;
                    data_s2_w0[4] <= fill_data_4;
                    data_s2_w0[5] <= fill_data_5;
                    data_s2_w0[6] <= fill_data_6;
                    data_s2_w0[7] <= fill_data_7;
                    data_s2_w0[8] <= fill_data_8;
                    data_s2_w0[9] <= fill_data_9;
                    data_s2_w0[10] <= fill_data_10;
                    data_s2_w0[11] <= fill_data_11;
                    data_s2_w0[12] <= fill_data_12;
                    data_s2_w0[13] <= fill_data_13;
                    data_s2_w0[14] <= fill_data_14;
                    data_s2_w0[15] <= fill_data_15;
                    data_s2_w0[16] <= fill_data_16;
                    data_s2_w0[17] <= fill_data_17;
                    data_s2_w0[18] <= fill_data_18;
                    data_s2_w0[19] <= fill_data_19;
                    data_s2_w0[20] <= fill_data_20;
                    data_s2_w0[21] <= fill_data_21;
                    data_s2_w0[22] <= fill_data_22;
                    data_s2_w0[23] <= fill_data_23;
                    data_s2_w0[24] <= fill_data_24;
                    data_s2_w0[25] <= fill_data_25;
                    data_s2_w0[26] <= fill_data_26;
                    data_s2_w0[27] <= fill_data_27;
                    data_s2_w0[28] <= fill_data_28;
                    data_s2_w0[29] <= fill_data_29;
                    data_s2_w0[30] <= fill_data_30;
                    data_s2_w0[31] <= fill_data_31;
                end
                if ((req_set == 3)) begin
                    valid_s3_w0 <= 1;
                    tag_s3_w0 <= req_tag;
                    data_s3_w0[0] <= fill_data_0;
                    data_s3_w0[1] <= fill_data_1;
                    data_s3_w0[2] <= fill_data_2;
                    data_s3_w0[3] <= fill_data_3;
                    data_s3_w0[4] <= fill_data_4;
                    data_s3_w0[5] <= fill_data_5;
                    data_s3_w0[6] <= fill_data_6;
                    data_s3_w0[7] <= fill_data_7;
                    data_s3_w0[8] <= fill_data_8;
                    data_s3_w0[9] <= fill_data_9;
                    data_s3_w0[10] <= fill_data_10;
                    data_s3_w0[11] <= fill_data_11;
                    data_s3_w0[12] <= fill_data_12;
                    data_s3_w0[13] <= fill_data_13;
                    data_s3_w0[14] <= fill_data_14;
                    data_s3_w0[15] <= fill_data_15;
                    data_s3_w0[16] <= fill_data_16;
                    data_s3_w0[17] <= fill_data_17;
                    data_s3_w0[18] <= fill_data_18;
                    data_s3_w0[19] <= fill_data_19;
                    data_s3_w0[20] <= fill_data_20;
                    data_s3_w0[21] <= fill_data_21;
                    data_s3_w0[22] <= fill_data_22;
                    data_s3_w0[23] <= fill_data_23;
                    data_s3_w0[24] <= fill_data_24;
                    data_s3_w0[25] <= fill_data_25;
                    data_s3_w0[26] <= fill_data_26;
                    data_s3_w0[27] <= fill_data_27;
                    data_s3_w0[28] <= fill_data_28;
                    data_s3_w0[29] <= fill_data_29;
                    data_s3_w0[30] <= fill_data_30;
                    data_s3_w0[31] <= fill_data_31;
                end
                if ((req_set == 4)) begin
                    valid_s4_w0 <= 1;
                    tag_s4_w0 <= req_tag;
                    data_s4_w0[0] <= fill_data_0;
                    data_s4_w0[1] <= fill_data_1;
                    data_s4_w0[2] <= fill_data_2;
                    data_s4_w0[3] <= fill_data_3;
                    data_s4_w0[4] <= fill_data_4;
                    data_s4_w0[5] <= fill_data_5;
                    data_s4_w0[6] <= fill_data_6;
                    data_s4_w0[7] <= fill_data_7;
                    data_s4_w0[8] <= fill_data_8;
                    data_s4_w0[9] <= fill_data_9;
                    data_s4_w0[10] <= fill_data_10;
                    data_s4_w0[11] <= fill_data_11;
                    data_s4_w0[12] <= fill_data_12;
                    data_s4_w0[13] <= fill_data_13;
                    data_s4_w0[14] <= fill_data_14;
                    data_s4_w0[15] <= fill_data_15;
                    data_s4_w0[16] <= fill_data_16;
                    data_s4_w0[17] <= fill_data_17;
                    data_s4_w0[18] <= fill_data_18;
                    data_s4_w0[19] <= fill_data_19;
                    data_s4_w0[20] <= fill_data_20;
                    data_s4_w0[21] <= fill_data_21;
                    data_s4_w0[22] <= fill_data_22;
                    data_s4_w0[23] <= fill_data_23;
                    data_s4_w0[24] <= fill_data_24;
                    data_s4_w0[25] <= fill_data_25;
                    data_s4_w0[26] <= fill_data_26;
                    data_s4_w0[27] <= fill_data_27;
                    data_s4_w0[28] <= fill_data_28;
                    data_s4_w0[29] <= fill_data_29;
                    data_s4_w0[30] <= fill_data_30;
                    data_s4_w0[31] <= fill_data_31;
                end
                if ((req_set == 5)) begin
                    valid_s5_w0 <= 1;
                    tag_s5_w0 <= req_tag;
                    data_s5_w0[0] <= fill_data_0;
                    data_s5_w0[1] <= fill_data_1;
                    data_s5_w0[2] <= fill_data_2;
                    data_s5_w0[3] <= fill_data_3;
                    data_s5_w0[4] <= fill_data_4;
                    data_s5_w0[5] <= fill_data_5;
                    data_s5_w0[6] <= fill_data_6;
                    data_s5_w0[7] <= fill_data_7;
                    data_s5_w0[8] <= fill_data_8;
                    data_s5_w0[9] <= fill_data_9;
                    data_s5_w0[10] <= fill_data_10;
                    data_s5_w0[11] <= fill_data_11;
                    data_s5_w0[12] <= fill_data_12;
                    data_s5_w0[13] <= fill_data_13;
                    data_s5_w0[14] <= fill_data_14;
                    data_s5_w0[15] <= fill_data_15;
                    data_s5_w0[16] <= fill_data_16;
                    data_s5_w0[17] <= fill_data_17;
                    data_s5_w0[18] <= fill_data_18;
                    data_s5_w0[19] <= fill_data_19;
                    data_s5_w0[20] <= fill_data_20;
                    data_s5_w0[21] <= fill_data_21;
                    data_s5_w0[22] <= fill_data_22;
                    data_s5_w0[23] <= fill_data_23;
                    data_s5_w0[24] <= fill_data_24;
                    data_s5_w0[25] <= fill_data_25;
                    data_s5_w0[26] <= fill_data_26;
                    data_s5_w0[27] <= fill_data_27;
                    data_s5_w0[28] <= fill_data_28;
                    data_s5_w0[29] <= fill_data_29;
                    data_s5_w0[30] <= fill_data_30;
                    data_s5_w0[31] <= fill_data_31;
                end
                if ((req_set == 6)) begin
                    valid_s6_w0 <= 1;
                    tag_s6_w0 <= req_tag;
                    data_s6_w0[0] <= fill_data_0;
                    data_s6_w0[1] <= fill_data_1;
                    data_s6_w0[2] <= fill_data_2;
                    data_s6_w0[3] <= fill_data_3;
                    data_s6_w0[4] <= fill_data_4;
                    data_s6_w0[5] <= fill_data_5;
                    data_s6_w0[6] <= fill_data_6;
                    data_s6_w0[7] <= fill_data_7;
                    data_s6_w0[8] <= fill_data_8;
                    data_s6_w0[9] <= fill_data_9;
                    data_s6_w0[10] <= fill_data_10;
                    data_s6_w0[11] <= fill_data_11;
                    data_s6_w0[12] <= fill_data_12;
                    data_s6_w0[13] <= fill_data_13;
                    data_s6_w0[14] <= fill_data_14;
                    data_s6_w0[15] <= fill_data_15;
                    data_s6_w0[16] <= fill_data_16;
                    data_s6_w0[17] <= fill_data_17;
                    data_s6_w0[18] <= fill_data_18;
                    data_s6_w0[19] <= fill_data_19;
                    data_s6_w0[20] <= fill_data_20;
                    data_s6_w0[21] <= fill_data_21;
                    data_s6_w0[22] <= fill_data_22;
                    data_s6_w0[23] <= fill_data_23;
                    data_s6_w0[24] <= fill_data_24;
                    data_s6_w0[25] <= fill_data_25;
                    data_s6_w0[26] <= fill_data_26;
                    data_s6_w0[27] <= fill_data_27;
                    data_s6_w0[28] <= fill_data_28;
                    data_s6_w0[29] <= fill_data_29;
                    data_s6_w0[30] <= fill_data_30;
                    data_s6_w0[31] <= fill_data_31;
                end
                if ((req_set == 7)) begin
                    valid_s7_w0 <= 1;
                    tag_s7_w0 <= req_tag;
                    data_s7_w0[0] <= fill_data_0;
                    data_s7_w0[1] <= fill_data_1;
                    data_s7_w0[2] <= fill_data_2;
                    data_s7_w0[3] <= fill_data_3;
                    data_s7_w0[4] <= fill_data_4;
                    data_s7_w0[5] <= fill_data_5;
                    data_s7_w0[6] <= fill_data_6;
                    data_s7_w0[7] <= fill_data_7;
                    data_s7_w0[8] <= fill_data_8;
                    data_s7_w0[9] <= fill_data_9;
                    data_s7_w0[10] <= fill_data_10;
                    data_s7_w0[11] <= fill_data_11;
                    data_s7_w0[12] <= fill_data_12;
                    data_s7_w0[13] <= fill_data_13;
                    data_s7_w0[14] <= fill_data_14;
                    data_s7_w0[15] <= fill_data_15;
                    data_s7_w0[16] <= fill_data_16;
                    data_s7_w0[17] <= fill_data_17;
                    data_s7_w0[18] <= fill_data_18;
                    data_s7_w0[19] <= fill_data_19;
                    data_s7_w0[20] <= fill_data_20;
                    data_s7_w0[21] <= fill_data_21;
                    data_s7_w0[22] <= fill_data_22;
                    data_s7_w0[23] <= fill_data_23;
                    data_s7_w0[24] <= fill_data_24;
                    data_s7_w0[25] <= fill_data_25;
                    data_s7_w0[26] <= fill_data_26;
                    data_s7_w0[27] <= fill_data_27;
                    data_s7_w0[28] <= fill_data_28;
                    data_s7_w0[29] <= fill_data_29;
                    data_s7_w0[30] <= fill_data_30;
                    data_s7_w0[31] <= fill_data_31;
                end
                if ((req_set == 8)) begin
                    valid_s8_w0 <= 1;
                    tag_s8_w0 <= req_tag;
                    data_s8_w0[0] <= fill_data_0;
                    data_s8_w0[1] <= fill_data_1;
                    data_s8_w0[2] <= fill_data_2;
                    data_s8_w0[3] <= fill_data_3;
                    data_s8_w0[4] <= fill_data_4;
                    data_s8_w0[5] <= fill_data_5;
                    data_s8_w0[6] <= fill_data_6;
                    data_s8_w0[7] <= fill_data_7;
                    data_s8_w0[8] <= fill_data_8;
                    data_s8_w0[9] <= fill_data_9;
                    data_s8_w0[10] <= fill_data_10;
                    data_s8_w0[11] <= fill_data_11;
                    data_s8_w0[12] <= fill_data_12;
                    data_s8_w0[13] <= fill_data_13;
                    data_s8_w0[14] <= fill_data_14;
                    data_s8_w0[15] <= fill_data_15;
                    data_s8_w0[16] <= fill_data_16;
                    data_s8_w0[17] <= fill_data_17;
                    data_s8_w0[18] <= fill_data_18;
                    data_s8_w0[19] <= fill_data_19;
                    data_s8_w0[20] <= fill_data_20;
                    data_s8_w0[21] <= fill_data_21;
                    data_s8_w0[22] <= fill_data_22;
                    data_s8_w0[23] <= fill_data_23;
                    data_s8_w0[24] <= fill_data_24;
                    data_s8_w0[25] <= fill_data_25;
                    data_s8_w0[26] <= fill_data_26;
                    data_s8_w0[27] <= fill_data_27;
                    data_s8_w0[28] <= fill_data_28;
                    data_s8_w0[29] <= fill_data_29;
                    data_s8_w0[30] <= fill_data_30;
                    data_s8_w0[31] <= fill_data_31;
                end
                if ((req_set == 9)) begin
                    valid_s9_w0 <= 1;
                    tag_s9_w0 <= req_tag;
                    data_s9_w0[0] <= fill_data_0;
                    data_s9_w0[1] <= fill_data_1;
                    data_s9_w0[2] <= fill_data_2;
                    data_s9_w0[3] <= fill_data_3;
                    data_s9_w0[4] <= fill_data_4;
                    data_s9_w0[5] <= fill_data_5;
                    data_s9_w0[6] <= fill_data_6;
                    data_s9_w0[7] <= fill_data_7;
                    data_s9_w0[8] <= fill_data_8;
                    data_s9_w0[9] <= fill_data_9;
                    data_s9_w0[10] <= fill_data_10;
                    data_s9_w0[11] <= fill_data_11;
                    data_s9_w0[12] <= fill_data_12;
                    data_s9_w0[13] <= fill_data_13;
                    data_s9_w0[14] <= fill_data_14;
                    data_s9_w0[15] <= fill_data_15;
                    data_s9_w0[16] <= fill_data_16;
                    data_s9_w0[17] <= fill_data_17;
                    data_s9_w0[18] <= fill_data_18;
                    data_s9_w0[19] <= fill_data_19;
                    data_s9_w0[20] <= fill_data_20;
                    data_s9_w0[21] <= fill_data_21;
                    data_s9_w0[22] <= fill_data_22;
                    data_s9_w0[23] <= fill_data_23;
                    data_s9_w0[24] <= fill_data_24;
                    data_s9_w0[25] <= fill_data_25;
                    data_s9_w0[26] <= fill_data_26;
                    data_s9_w0[27] <= fill_data_27;
                    data_s9_w0[28] <= fill_data_28;
                    data_s9_w0[29] <= fill_data_29;
                    data_s9_w0[30] <= fill_data_30;
                    data_s9_w0[31] <= fill_data_31;
                end
                if ((req_set == 10)) begin
                    valid_s10_w0 <= 1;
                    tag_s10_w0 <= req_tag;
                    data_s10_w0[0] <= fill_data_0;
                    data_s10_w0[1] <= fill_data_1;
                    data_s10_w0[2] <= fill_data_2;
                    data_s10_w0[3] <= fill_data_3;
                    data_s10_w0[4] <= fill_data_4;
                    data_s10_w0[5] <= fill_data_5;
                    data_s10_w0[6] <= fill_data_6;
                    data_s10_w0[7] <= fill_data_7;
                    data_s10_w0[8] <= fill_data_8;
                    data_s10_w0[9] <= fill_data_9;
                    data_s10_w0[10] <= fill_data_10;
                    data_s10_w0[11] <= fill_data_11;
                    data_s10_w0[12] <= fill_data_12;
                    data_s10_w0[13] <= fill_data_13;
                    data_s10_w0[14] <= fill_data_14;
                    data_s10_w0[15] <= fill_data_15;
                    data_s10_w0[16] <= fill_data_16;
                    data_s10_w0[17] <= fill_data_17;
                    data_s10_w0[18] <= fill_data_18;
                    data_s10_w0[19] <= fill_data_19;
                    data_s10_w0[20] <= fill_data_20;
                    data_s10_w0[21] <= fill_data_21;
                    data_s10_w0[22] <= fill_data_22;
                    data_s10_w0[23] <= fill_data_23;
                    data_s10_w0[24] <= fill_data_24;
                    data_s10_w0[25] <= fill_data_25;
                    data_s10_w0[26] <= fill_data_26;
                    data_s10_w0[27] <= fill_data_27;
                    data_s10_w0[28] <= fill_data_28;
                    data_s10_w0[29] <= fill_data_29;
                    data_s10_w0[30] <= fill_data_30;
                    data_s10_w0[31] <= fill_data_31;
                end
                if ((req_set == 11)) begin
                    valid_s11_w0 <= 1;
                    tag_s11_w0 <= req_tag;
                    data_s11_w0[0] <= fill_data_0;
                    data_s11_w0[1] <= fill_data_1;
                    data_s11_w0[2] <= fill_data_2;
                    data_s11_w0[3] <= fill_data_3;
                    data_s11_w0[4] <= fill_data_4;
                    data_s11_w0[5] <= fill_data_5;
                    data_s11_w0[6] <= fill_data_6;
                    data_s11_w0[7] <= fill_data_7;
                    data_s11_w0[8] <= fill_data_8;
                    data_s11_w0[9] <= fill_data_9;
                    data_s11_w0[10] <= fill_data_10;
                    data_s11_w0[11] <= fill_data_11;
                    data_s11_w0[12] <= fill_data_12;
                    data_s11_w0[13] <= fill_data_13;
                    data_s11_w0[14] <= fill_data_14;
                    data_s11_w0[15] <= fill_data_15;
                    data_s11_w0[16] <= fill_data_16;
                    data_s11_w0[17] <= fill_data_17;
                    data_s11_w0[18] <= fill_data_18;
                    data_s11_w0[19] <= fill_data_19;
                    data_s11_w0[20] <= fill_data_20;
                    data_s11_w0[21] <= fill_data_21;
                    data_s11_w0[22] <= fill_data_22;
                    data_s11_w0[23] <= fill_data_23;
                    data_s11_w0[24] <= fill_data_24;
                    data_s11_w0[25] <= fill_data_25;
                    data_s11_w0[26] <= fill_data_26;
                    data_s11_w0[27] <= fill_data_27;
                    data_s11_w0[28] <= fill_data_28;
                    data_s11_w0[29] <= fill_data_29;
                    data_s11_w0[30] <= fill_data_30;
                    data_s11_w0[31] <= fill_data_31;
                end
                if ((req_set == 12)) begin
                    valid_s12_w0 <= 1;
                    tag_s12_w0 <= req_tag;
                    data_s12_w0[0] <= fill_data_0;
                    data_s12_w0[1] <= fill_data_1;
                    data_s12_w0[2] <= fill_data_2;
                    data_s12_w0[3] <= fill_data_3;
                    data_s12_w0[4] <= fill_data_4;
                    data_s12_w0[5] <= fill_data_5;
                    data_s12_w0[6] <= fill_data_6;
                    data_s12_w0[7] <= fill_data_7;
                    data_s12_w0[8] <= fill_data_8;
                    data_s12_w0[9] <= fill_data_9;
                    data_s12_w0[10] <= fill_data_10;
                    data_s12_w0[11] <= fill_data_11;
                    data_s12_w0[12] <= fill_data_12;
                    data_s12_w0[13] <= fill_data_13;
                    data_s12_w0[14] <= fill_data_14;
                    data_s12_w0[15] <= fill_data_15;
                    data_s12_w0[16] <= fill_data_16;
                    data_s12_w0[17] <= fill_data_17;
                    data_s12_w0[18] <= fill_data_18;
                    data_s12_w0[19] <= fill_data_19;
                    data_s12_w0[20] <= fill_data_20;
                    data_s12_w0[21] <= fill_data_21;
                    data_s12_w0[22] <= fill_data_22;
                    data_s12_w0[23] <= fill_data_23;
                    data_s12_w0[24] <= fill_data_24;
                    data_s12_w0[25] <= fill_data_25;
                    data_s12_w0[26] <= fill_data_26;
                    data_s12_w0[27] <= fill_data_27;
                    data_s12_w0[28] <= fill_data_28;
                    data_s12_w0[29] <= fill_data_29;
                    data_s12_w0[30] <= fill_data_30;
                    data_s12_w0[31] <= fill_data_31;
                end
                if ((req_set == 13)) begin
                    valid_s13_w0 <= 1;
                    tag_s13_w0 <= req_tag;
                    data_s13_w0[0] <= fill_data_0;
                    data_s13_w0[1] <= fill_data_1;
                    data_s13_w0[2] <= fill_data_2;
                    data_s13_w0[3] <= fill_data_3;
                    data_s13_w0[4] <= fill_data_4;
                    data_s13_w0[5] <= fill_data_5;
                    data_s13_w0[6] <= fill_data_6;
                    data_s13_w0[7] <= fill_data_7;
                    data_s13_w0[8] <= fill_data_8;
                    data_s13_w0[9] <= fill_data_9;
                    data_s13_w0[10] <= fill_data_10;
                    data_s13_w0[11] <= fill_data_11;
                    data_s13_w0[12] <= fill_data_12;
                    data_s13_w0[13] <= fill_data_13;
                    data_s13_w0[14] <= fill_data_14;
                    data_s13_w0[15] <= fill_data_15;
                    data_s13_w0[16] <= fill_data_16;
                    data_s13_w0[17] <= fill_data_17;
                    data_s13_w0[18] <= fill_data_18;
                    data_s13_w0[19] <= fill_data_19;
                    data_s13_w0[20] <= fill_data_20;
                    data_s13_w0[21] <= fill_data_21;
                    data_s13_w0[22] <= fill_data_22;
                    data_s13_w0[23] <= fill_data_23;
                    data_s13_w0[24] <= fill_data_24;
                    data_s13_w0[25] <= fill_data_25;
                    data_s13_w0[26] <= fill_data_26;
                    data_s13_w0[27] <= fill_data_27;
                    data_s13_w0[28] <= fill_data_28;
                    data_s13_w0[29] <= fill_data_29;
                    data_s13_w0[30] <= fill_data_30;
                    data_s13_w0[31] <= fill_data_31;
                end
                if ((req_set == 14)) begin
                    valid_s14_w0 <= 1;
                    tag_s14_w0 <= req_tag;
                    data_s14_w0[0] <= fill_data_0;
                    data_s14_w0[1] <= fill_data_1;
                    data_s14_w0[2] <= fill_data_2;
                    data_s14_w0[3] <= fill_data_3;
                    data_s14_w0[4] <= fill_data_4;
                    data_s14_w0[5] <= fill_data_5;
                    data_s14_w0[6] <= fill_data_6;
                    data_s14_w0[7] <= fill_data_7;
                    data_s14_w0[8] <= fill_data_8;
                    data_s14_w0[9] <= fill_data_9;
                    data_s14_w0[10] <= fill_data_10;
                    data_s14_w0[11] <= fill_data_11;
                    data_s14_w0[12] <= fill_data_12;
                    data_s14_w0[13] <= fill_data_13;
                    data_s14_w0[14] <= fill_data_14;
                    data_s14_w0[15] <= fill_data_15;
                    data_s14_w0[16] <= fill_data_16;
                    data_s14_w0[17] <= fill_data_17;
                    data_s14_w0[18] <= fill_data_18;
                    data_s14_w0[19] <= fill_data_19;
                    data_s14_w0[20] <= fill_data_20;
                    data_s14_w0[21] <= fill_data_21;
                    data_s14_w0[22] <= fill_data_22;
                    data_s14_w0[23] <= fill_data_23;
                    data_s14_w0[24] <= fill_data_24;
                    data_s14_w0[25] <= fill_data_25;
                    data_s14_w0[26] <= fill_data_26;
                    data_s14_w0[27] <= fill_data_27;
                    data_s14_w0[28] <= fill_data_28;
                    data_s14_w0[29] <= fill_data_29;
                    data_s14_w0[30] <= fill_data_30;
                    data_s14_w0[31] <= fill_data_31;
                end
                if ((req_set == 15)) begin
                    valid_s15_w0 <= 1;
                    tag_s15_w0 <= req_tag;
                    data_s15_w0[0] <= fill_data_0;
                    data_s15_w0[1] <= fill_data_1;
                    data_s15_w0[2] <= fill_data_2;
                    data_s15_w0[3] <= fill_data_3;
                    data_s15_w0[4] <= fill_data_4;
                    data_s15_w0[5] <= fill_data_5;
                    data_s15_w0[6] <= fill_data_6;
                    data_s15_w0[7] <= fill_data_7;
                    data_s15_w0[8] <= fill_data_8;
                    data_s15_w0[9] <= fill_data_9;
                    data_s15_w0[10] <= fill_data_10;
                    data_s15_w0[11] <= fill_data_11;
                    data_s15_w0[12] <= fill_data_12;
                    data_s15_w0[13] <= fill_data_13;
                    data_s15_w0[14] <= fill_data_14;
                    data_s15_w0[15] <= fill_data_15;
                    data_s15_w0[16] <= fill_data_16;
                    data_s15_w0[17] <= fill_data_17;
                    data_s15_w0[18] <= fill_data_18;
                    data_s15_w0[19] <= fill_data_19;
                    data_s15_w0[20] <= fill_data_20;
                    data_s15_w0[21] <= fill_data_21;
                    data_s15_w0[22] <= fill_data_22;
                    data_s15_w0[23] <= fill_data_23;
                    data_s15_w0[24] <= fill_data_24;
                    data_s15_w0[25] <= fill_data_25;
                    data_s15_w0[26] <= fill_data_26;
                    data_s15_w0[27] <= fill_data_27;
                    data_s15_w0[28] <= fill_data_28;
                    data_s15_w0[29] <= fill_data_29;
                    data_s15_w0[30] <= fill_data_30;
                    data_s15_w0[31] <= fill_data_31;
                end
                state <= 0;
            end
        end
    end

endmodule

module SharedMemory (
    input clk,
    input rst_n,
    input [13:0] rd_addr,
    input rd_valid,
    input [13:0] wr_addr,
    input [31:0] wr_data,
    input wr_en,
    output [31:0] rd_data
);

    reg [31:0] bank_0 [0:1023];
    reg [31:0] bank_1 [0:1023];
    reg [31:0] bank_2 [0:1023];
    reg [31:0] bank_3 [0:1023];
    reg [31:0] bank_4 [0:1023];
    reg [31:0] bank_5 [0:1023];
    reg [31:0] bank_6 [0:1023];
    reg [31:0] bank_7 [0:1023];
    reg [31:0] bank_8 [0:1023];
    reg [31:0] bank_9 [0:1023];
    reg [31:0] bank_10 [0:1023];
    reg [31:0] bank_11 [0:1023];
    reg [31:0] bank_12 [0:1023];
    reg [31:0] bank_13 [0:1023];
    reg [31:0] bank_14 [0:1023];
    reg [31:0] bank_15 [0:1023];

    logic [3:0] bank_sel;
    logic [9:0] bank_addr;

    always @(*) begin
        case (bank_sel)
            15: rd_data = bank_15[bank_addr];
            14: rd_data = bank_14[bank_addr];
            13: rd_data = bank_13[bank_addr];
            12: rd_data = bank_12[bank_addr];
            11: rd_data = bank_11[bank_addr];
            10: rd_data = bank_10[bank_addr];
            9: rd_data = bank_9[bank_addr];
            8: rd_data = bank_8[bank_addr];
            7: rd_data = bank_7[bank_addr];
            6: rd_data = bank_6[bank_addr];
            5: rd_data = bank_5[bank_addr];
            4: rd_data = bank_4[bank_addr];
            3: rd_data = bank_3[bank_addr];
            2: rd_data = bank_2[bank_addr];
            1: rd_data = bank_1[bank_addr];
            default: rd_data = bank_0[bank_addr];
        endcase
    end
    assign bank_sel = rd_addr[3:0];
    assign bank_addr = (rd_addr >> 4);

    always @(posedge clk or negedge rst_n) begin
        if ((bank_sel == 0)) begin
            if (wr_en) begin
                bank_0[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 1)) begin
            if (wr_en) begin
                bank_1[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 2)) begin
            if (wr_en) begin
                bank_2[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 3)) begin
            if (wr_en) begin
                bank_3[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 4)) begin
            if (wr_en) begin
                bank_4[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 5)) begin
            if (wr_en) begin
                bank_5[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 6)) begin
            if (wr_en) begin
                bank_6[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 7)) begin
            if (wr_en) begin
                bank_7[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 8)) begin
            if (wr_en) begin
                bank_8[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 9)) begin
            if (wr_en) begin
                bank_9[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 10)) begin
            if (wr_en) begin
                bank_10[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 11)) begin
            if (wr_en) begin
                bank_11[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 12)) begin
            if (wr_en) begin
                bank_12[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 13)) begin
            if (wr_en) begin
                bank_13[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 14)) begin
            if (wr_en) begin
                bank_14[bank_addr] <= wr_data;
            end
        end
        if ((bank_sel == 15)) begin
            if (wr_en) begin
                bank_15[bank_addr] <= wr_data;
            end
        end
    end

endmodule

module GPGPUCore (
    input clk,
    input rst_n,
    input launch_valid,
    input [1:0] launch_warps,
    input [15:0] launch_pc,
    input prog_load_valid,
    input [15:0] prog_load_addr,
    input [63:0] prog_load_data,
    input prog_load_we,
    input mem_resp_valid,
    input [31:0] mem_resp_data,
    output kernel_done,
    output busy,
    output mem_req_valid,
    output mem_req_is_store,
    output [31:0] mem_req_addr,
    output [31:0] mem_req_data,
    output [3:0] mem_req_mask
);

    logic [1:0] wb_sel;
    reg tensor_cmd;
    reg [1:0] tensor_phase;

    assign clk = clk;
    assign rst_n = rst_n;
    assign clk = clk;
    assign rst_n = rst_n;
    assign clk = clk;
    assign rst_n = rst_n;
    assign clk = clk;
    assign rst_n = rst_n;
    assign clk = clk;
    assign rst_n = rst_n;
    assign clk = clk;
    assign rst_n = rst_n;
    assign clk = clk;
    assign rst_n = rst_n;
    assign clk = clk;
    assign rst_n = rst_n;
    assign clk = clk;
    assign rst_n = rst_n;
    assign clk = clk;
    assign rst_n = rst_n;
    assign launch_valid = launch_valid;
    assign launch_warps = launch_warps;
    assign launch_pc = launch_pc;
    assign kernel_done = kernel_done;
    assign fetch_valid = fetch_valid;
    assign fetch_warp = fetch_warp;
    assign fetch_pc = fetch_pc;
    assign fetch_ready = fetch_ready;
    assign issue_ready = issue_ready;
    assign issue_warp = dec_warp;
    assign issue_pc = dec_pc;
    assign issue_mask = dec_pred_use;
    assign issue_valid = dec_valid;
    assign issue_warp = dec_warp;
    assign issue_dst = dec_dst;
    assign issue_src_a = dec_src_a;
    assign issue_src_b = dec_src_b;
    assign issue_src_c = dec_src_c;
    assign wb_valid = ((out_valid | out_valid) | done);
    assign wb_warp = dec_warp;
    assign wb_dst = dec_dst;
    assign rd_addr_a = dec_src_a;
    assign rd_addr_b = dec_src_b;
    assign wb_sel = (out_valid ? 0 : (out_valid ? 1 : 2));
    always @(*) begin
        case (wb_sel)
            0: wr_addr = dec_dst;
            default: wr_addr = 0;
        endcase
    end
    always @(*) begin
        case (wb_sel)
            0: wr_data_0 = result_0;
            1: wr_data_0 = result_0;
            default: wr_data_0 = store_data_0;
        endcase
    end
    assign wr_en[0] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[0]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_1 = result_1;
            1: wr_data_1 = result_1;
            default: wr_data_1 = store_data_1;
        endcase
    end
    assign wr_en[1] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[1]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_2 = result_2;
            1: wr_data_2 = result_2;
            default: wr_data_2 = store_data_2;
        endcase
    end
    assign wr_en[2] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[2]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_3 = result_3;
            1: wr_data_3 = result_3;
            default: wr_data_3 = store_data_3;
        endcase
    end
    assign wr_en[3] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[3]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_4 = result_4;
            1: wr_data_4 = result_4;
            default: wr_data_4 = store_data_4;
        endcase
    end
    assign wr_en[4] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[4]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_5 = result_5;
            1: wr_data_5 = result_5;
            default: wr_data_5 = store_data_5;
        endcase
    end
    assign wr_en[5] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[5]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_6 = result_6;
            1: wr_data_6 = result_6;
            default: wr_data_6 = store_data_6;
        endcase
    end
    assign wr_en[6] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[6]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_7 = result_7;
            1: wr_data_7 = result_7;
            default: wr_data_7 = store_data_7;
        endcase
    end
    assign wr_en[7] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[7]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_8 = result_8;
            1: wr_data_8 = result_8;
            default: wr_data_8 = store_data_8;
        endcase
    end
    assign wr_en[8] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[8]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_9 = result_9;
            1: wr_data_9 = result_9;
            default: wr_data_9 = store_data_9;
        endcase
    end
    assign wr_en[9] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[9]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_10 = result_10;
            1: wr_data_10 = result_10;
            default: wr_data_10 = store_data_10;
        endcase
    end
    assign wr_en[10] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[10]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_11 = result_11;
            1: wr_data_11 = result_11;
            default: wr_data_11 = store_data_11;
        endcase
    end
    assign wr_en[11] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[11]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_12 = result_12;
            1: wr_data_12 = result_12;
            default: wr_data_12 = store_data_12;
        endcase
    end
    assign wr_en[12] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[12]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_13 = result_13;
            1: wr_data_13 = result_13;
            default: wr_data_13 = store_data_13;
        endcase
    end
    assign wr_en[13] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[13]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_14 = result_14;
            1: wr_data_14 = result_14;
            default: wr_data_14 = store_data_14;
        endcase
    end
    assign wr_en[14] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[14]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_15 = result_15;
            1: wr_data_15 = result_15;
            default: wr_data_15 = store_data_15;
        endcase
    end
    assign wr_en[15] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[15]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_16 = result_16;
            1: wr_data_16 = result_16;
            default: wr_data_16 = 0;
        endcase
    end
    assign wr_en[16] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[16]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_17 = result_17;
            1: wr_data_17 = result_17;
            default: wr_data_17 = 0;
        endcase
    end
    assign wr_en[17] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[17]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_18 = result_18;
            1: wr_data_18 = result_18;
            default: wr_data_18 = 0;
        endcase
    end
    assign wr_en[18] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[18]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_19 = result_19;
            1: wr_data_19 = result_19;
            default: wr_data_19 = 0;
        endcase
    end
    assign wr_en[19] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[19]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_20 = result_20;
            1: wr_data_20 = result_20;
            default: wr_data_20 = 0;
        endcase
    end
    assign wr_en[20] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[20]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_21 = result_21;
            1: wr_data_21 = result_21;
            default: wr_data_21 = 0;
        endcase
    end
    assign wr_en[21] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[21]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_22 = result_22;
            1: wr_data_22 = result_22;
            default: wr_data_22 = 0;
        endcase
    end
    assign wr_en[22] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[22]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_23 = result_23;
            1: wr_data_23 = result_23;
            default: wr_data_23 = 0;
        endcase
    end
    assign wr_en[23] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[23]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_24 = result_24;
            1: wr_data_24 = result_24;
            default: wr_data_24 = 0;
        endcase
    end
    assign wr_en[24] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[24]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_25 = result_25;
            1: wr_data_25 = result_25;
            default: wr_data_25 = 0;
        endcase
    end
    assign wr_en[25] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[25]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_26 = result_26;
            1: wr_data_26 = result_26;
            default: wr_data_26 = 0;
        endcase
    end
    assign wr_en[26] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[26]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_27 = result_27;
            1: wr_data_27 = result_27;
            default: wr_data_27 = 0;
        endcase
    end
    assign wr_en[27] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[27]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_28 = result_28;
            1: wr_data_28 = result_28;
            default: wr_data_28 = 0;
        endcase
    end
    assign wr_en[28] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[28]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_29 = result_29;
            1: wr_data_29 = result_29;
            default: wr_data_29 = 0;
        endcase
    end
    assign wr_en[29] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[29]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_30 = result_30;
            1: wr_data_30 = result_30;
            default: wr_data_30 = 0;
        endcase
    end
    assign wr_en[30] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[30]);
    always @(*) begin
        case (wb_sel)
            0: wr_data_31 = result_31;
            1: wr_data_31 = result_31;
            default: wr_data_31 = 0;
        endcase
    end
    assign wr_en[31] = (((((wb_sel == 0) & out_valid) | ((wb_sel == 1) & out_valid)) | ((wb_sel == 2) & store_valid)) & issue_mask[31]);
    assign valid = (dec_valid & (dec_unit == 0));
    assign op = dec_func;
    assign shift_amt = dec_imm[4:0];
    assign src_a_0 = rd_data_a_0;
    assign src_b_0 = rd_data_b_0;
    assign src_c_0 = 0;
    assign src_a_1 = rd_data_a_1;
    assign src_b_1 = rd_data_b_1;
    assign src_c_1 = 0;
    assign src_a_2 = rd_data_a_2;
    assign src_b_2 = rd_data_b_2;
    assign src_c_2 = 0;
    assign src_a_3 = rd_data_a_3;
    assign src_b_3 = rd_data_b_3;
    assign src_c_3 = 0;
    assign src_a_4 = rd_data_a_4;
    assign src_b_4 = rd_data_b_4;
    assign src_c_4 = 0;
    assign src_a_5 = rd_data_a_5;
    assign src_b_5 = rd_data_b_5;
    assign src_c_5 = 0;
    assign src_a_6 = rd_data_a_6;
    assign src_b_6 = rd_data_b_6;
    assign src_c_6 = 0;
    assign src_a_7 = rd_data_a_7;
    assign src_b_7 = rd_data_b_7;
    assign src_c_7 = 0;
    assign src_a_8 = rd_data_a_8;
    assign src_b_8 = rd_data_b_8;
    assign src_c_8 = 0;
    assign src_a_9 = rd_data_a_9;
    assign src_b_9 = rd_data_b_9;
    assign src_c_9 = 0;
    assign src_a_10 = rd_data_a_10;
    assign src_b_10 = rd_data_b_10;
    assign src_c_10 = 0;
    assign src_a_11 = rd_data_a_11;
    assign src_b_11 = rd_data_b_11;
    assign src_c_11 = 0;
    assign src_a_12 = rd_data_a_12;
    assign src_b_12 = rd_data_b_12;
    assign src_c_12 = 0;
    assign src_a_13 = rd_data_a_13;
    assign src_b_13 = rd_data_b_13;
    assign src_c_13 = 0;
    assign src_a_14 = rd_data_a_14;
    assign src_b_14 = rd_data_b_14;
    assign src_c_14 = 0;
    assign src_a_15 = rd_data_a_15;
    assign src_b_15 = rd_data_b_15;
    assign src_c_15 = 0;
    assign src_a_16 = rd_data_a_16;
    assign src_b_16 = rd_data_b_16;
    assign src_c_16 = 0;
    assign src_a_17 = rd_data_a_17;
    assign src_b_17 = rd_data_b_17;
    assign src_c_17 = 0;
    assign src_a_18 = rd_data_a_18;
    assign src_b_18 = rd_data_b_18;
    assign src_c_18 = 0;
    assign src_a_19 = rd_data_a_19;
    assign src_b_19 = rd_data_b_19;
    assign src_c_19 = 0;
    assign src_a_20 = rd_data_a_20;
    assign src_b_20 = rd_data_b_20;
    assign src_c_20 = 0;
    assign src_a_21 = rd_data_a_21;
    assign src_b_21 = rd_data_b_21;
    assign src_c_21 = 0;
    assign src_a_22 = rd_data_a_22;
    assign src_b_22 = rd_data_b_22;
    assign src_c_22 = 0;
    assign src_a_23 = rd_data_a_23;
    assign src_b_23 = rd_data_b_23;
    assign src_c_23 = 0;
    assign src_a_24 = rd_data_a_24;
    assign src_b_24 = rd_data_b_24;
    assign src_c_24 = 0;
    assign src_a_25 = rd_data_a_25;
    assign src_b_25 = rd_data_b_25;
    assign src_c_25 = 0;
    assign src_a_26 = rd_data_a_26;
    assign src_b_26 = rd_data_b_26;
    assign src_c_26 = 0;
    assign src_a_27 = rd_data_a_27;
    assign src_b_27 = rd_data_b_27;
    assign src_c_27 = 0;
    assign src_a_28 = rd_data_a_28;
    assign src_b_28 = rd_data_b_28;
    assign src_c_28 = 0;
    assign src_a_29 = rd_data_a_29;
    assign src_b_29 = rd_data_b_29;
    assign src_c_29 = 0;
    assign src_a_30 = rd_data_a_30;
    assign src_b_30 = rd_data_b_30;
    assign src_c_30 = 0;
    assign src_a_31 = rd_data_a_31;
    assign src_b_31 = rd_data_b_31;
    assign src_c_31 = 0;
    assign pred_mask = issue_mask;
    assign valid = (dec_valid & (dec_unit == 1));
    assign op = dec_func;
    assign src_0 = rd_data_a_0;
    assign src_1 = rd_data_a_1;
    assign src_2 = rd_data_a_2;
    assign src_3 = rd_data_a_3;
    assign src_4 = rd_data_a_4;
    assign src_5 = rd_data_a_5;
    assign src_6 = rd_data_a_6;
    assign src_7 = rd_data_a_7;
    assign src_8 = rd_data_a_8;
    assign src_9 = rd_data_a_9;
    assign src_10 = rd_data_a_10;
    assign src_11 = rd_data_a_11;
    assign src_12 = rd_data_a_12;
    assign src_13 = rd_data_a_13;
    assign src_14 = rd_data_a_14;
    assign src_15 = rd_data_a_15;
    assign src_16 = rd_data_a_16;
    assign src_17 = rd_data_a_17;
    assign src_18 = rd_data_a_18;
    assign src_19 = rd_data_a_19;
    assign src_20 = rd_data_a_20;
    assign src_21 = rd_data_a_21;
    assign src_22 = rd_data_a_22;
    assign src_23 = rd_data_a_23;
    assign src_24 = rd_data_a_24;
    assign src_25 = rd_data_a_25;
    assign src_26 = rd_data_a_26;
    assign src_27 = rd_data_a_27;
    assign src_28 = rd_data_a_28;
    assign src_29 = rd_data_a_29;
    assign src_30 = rd_data_a_30;
    assign src_31 = rd_data_a_31;
    assign start = (dec_valid & (dec_unit == 2));
    assign op = dec_func;
    assign load_valid = tensor_cmd;
    assign load_done = tensor_cmd;
    assign store_ready = 1;
    assign load_data_0 = rd_data_a_0;
    assign load_data_1 = rd_data_a_1;
    assign load_data_2 = rd_data_a_2;
    assign load_data_3 = rd_data_a_3;
    assign load_data_4 = rd_data_a_4;
    assign load_data_5 = rd_data_a_5;
    assign load_data_6 = rd_data_a_6;
    assign load_data_7 = rd_data_a_7;
    assign load_data_8 = rd_data_a_8;
    assign load_data_9 = rd_data_a_9;
    assign load_data_10 = rd_data_a_10;
    assign load_data_11 = rd_data_a_11;
    assign load_data_12 = rd_data_a_12;
    assign load_data_13 = rd_data_a_13;
    assign load_data_14 = rd_data_a_14;
    assign load_data_15 = rd_data_a_15;
    assign load_data_16 = rd_data_a_16;
    assign load_data_17 = rd_data_a_17;
    assign load_data_18 = rd_data_a_18;
    assign load_data_19 = rd_data_a_19;
    assign load_data_20 = rd_data_a_20;
    assign load_data_21 = rd_data_a_21;
    assign load_data_22 = rd_data_a_22;
    assign load_data_23 = rd_data_a_23;
    assign load_data_24 = rd_data_a_24;
    assign load_data_25 = rd_data_a_25;
    assign load_data_26 = rd_data_a_26;
    assign load_data_27 = rd_data_a_27;
    assign load_data_28 = rd_data_a_28;
    assign load_data_29 = rd_data_a_29;
    assign load_data_30 = rd_data_a_30;
    assign load_data_31 = rd_data_a_31;
    assign req_valid = (dec_valid & (dec_unit == 3));
    assign req_is_store = (dec_func == 1);
    assign req_addr_0 = rd_data_a_0;
    assign req_data_0 = rd_data_b_0;
    assign req_addr_1 = rd_data_a_1;
    assign req_data_1 = rd_data_b_1;
    assign req_addr_2 = rd_data_a_2;
    assign req_data_2 = rd_data_b_2;
    assign req_addr_3 = rd_data_a_3;
    assign req_data_3 = rd_data_b_3;
    assign req_addr_4 = rd_data_a_4;
    assign req_data_4 = rd_data_b_4;
    assign req_addr_5 = rd_data_a_5;
    assign req_data_5 = rd_data_b_5;
    assign req_addr_6 = rd_data_a_6;
    assign req_data_6 = rd_data_b_6;
    assign req_addr_7 = rd_data_a_7;
    assign req_data_7 = rd_data_b_7;
    assign req_addr_8 = rd_data_a_8;
    assign req_data_8 = rd_data_b_8;
    assign req_addr_9 = rd_data_a_9;
    assign req_data_9 = rd_data_b_9;
    assign req_addr_10 = rd_data_a_10;
    assign req_data_10 = rd_data_b_10;
    assign req_addr_11 = rd_data_a_11;
    assign req_data_11 = rd_data_b_11;
    assign req_addr_12 = rd_data_a_12;
    assign req_data_12 = rd_data_b_12;
    assign req_addr_13 = rd_data_a_13;
    assign req_data_13 = rd_data_b_13;
    assign req_addr_14 = rd_data_a_14;
    assign req_data_14 = rd_data_b_14;
    assign req_addr_15 = rd_data_a_15;
    assign req_data_15 = rd_data_b_15;
    assign req_addr_16 = rd_data_a_16;
    assign req_data_16 = rd_data_b_16;
    assign req_addr_17 = rd_data_a_17;
    assign req_data_17 = rd_data_b_17;
    assign req_addr_18 = rd_data_a_18;
    assign req_data_18 = rd_data_b_18;
    assign req_addr_19 = rd_data_a_19;
    assign req_data_19 = rd_data_b_19;
    assign req_addr_20 = rd_data_a_20;
    assign req_data_20 = rd_data_b_20;
    assign req_addr_21 = rd_data_a_21;
    assign req_data_21 = rd_data_b_21;
    assign req_addr_22 = rd_data_a_22;
    assign req_data_22 = rd_data_b_22;
    assign req_addr_23 = rd_data_a_23;
    assign req_data_23 = rd_data_b_23;
    assign req_addr_24 = rd_data_a_24;
    assign req_data_24 = rd_data_b_24;
    assign req_addr_25 = rd_data_a_25;
    assign req_data_25 = rd_data_b_25;
    assign req_addr_26 = rd_data_a_26;
    assign req_data_26 = rd_data_b_26;
    assign req_addr_27 = rd_data_a_27;
    assign req_data_27 = rd_data_b_27;
    assign req_addr_28 = rd_data_a_28;
    assign req_data_28 = rd_data_b_28;
    assign req_addr_29 = rd_data_a_29;
    assign req_data_29 = rd_data_b_29;
    assign req_addr_30 = rd_data_a_30;
    assign req_data_30 = rd_data_b_30;
    assign req_addr_31 = rd_data_a_31;
    assign req_data_31 = rd_data_b_31;
    assign req_mask = issue_mask;
    assign req_valid = out_valid;
    assign req_is_store = out_is_store;
    assign req_addr = out_addr;
    assign req_data = out_data_0;
    assign req_mask = out_mask;
    assign mem_req_valid = miss_valid;
    assign mem_req_is_store = req_is_store;
    assign mem_req_addr = miss_addr;
    assign mem_req_data = req_data;
    assign mem_req_mask = req_mask;
    assign fill_valid = mem_resp_valid;
    assign fill_addr = mem_req_addr;
    assign fill_data_0 = mem_resp_data;
    assign imem_resp_valid = (prog_load_valid & prog_load_we);
    assign imem_resp_data = prog_load_data;
    assign busy = (~kernel_done);
    RegisterFile regfile (
        .clk(clk),
        .rst_n(rst_n)
    );

    ALUArray alu (
        .clk(clk),
        .rst_n(rst_n)
    );

    SFUArray sfu (
        .clk(clk),
        .rst_n(rst_n)
    );

    TensorCore tensor (
        .clk(clk),
        .rst_n(rst_n),
        .busy(busy)
    );

    WarpScheduler scheduler (
        .clk(clk),
        .rst_n(rst_n),
        .launch_valid(launch_valid),
        .launch_warps(launch_warps),
        .launch_pc(launch_pc),
        .kernel_done(kernel_done)
    );

    Scoreboard scoreboard (
        .clk(clk),
        .rst_n(rst_n)
    );

    Frontend frontend (
        .clk(clk),
        .rst_n(rst_n)
    );

    MemoryCoalescer coalescer (
        .clk(clk),
        .rst_n(rst_n)
    );

    L1Cache l1cache (
        .clk(clk),
        .rst_n(rst_n)
    );

    SharedMemory smem (
        .clk(clk),
        .rst_n(rst_n)
    );

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            tensor_cmd <= 0;
            tensor_phase <= 0;
        end else begin
            if ((dec_valid & (dec_unit == 2))) begin
                tensor_cmd <= 1;
                tensor_phase <= 0;
            end
            if (tensor_cmd) begin
                if ((tensor_phase < 3)) begin
                    tensor_phase <= (tensor_phase + 1);
                end else begin
                    tensor_cmd <= 0;
                end
            end
        end
    end

endmodule