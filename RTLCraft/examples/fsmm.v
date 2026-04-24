module FSMMFetchUnit (
    input [2047:0] w_reg,
    input [1279:0] idx_reg,
    input [4:0] p1_base_c,
    input [4:0] max_k,
    output [127:0] w_val_vec_flat,
    output [79:0] w_row_vec_flat,
    output [79:0] c_vec_flat
);

    logic [4:0] c_vec [0:15];
    logic [4:0] k_vec [0:15];
    logic [127:0] w_col_sel [0:15];
    logic [79:0] idx_col_sel [0:15];
    logic [7:0] w_val_vec_arr [0:15];
    logic [4:0] w_row_vec_arr [0:15];

    assign w_col_0 = w_reg[127:0];
    assign idx_col_0 = idx_reg[79:0];
    assign w_col_1 = w_reg[255:128];
    assign idx_col_1 = idx_reg[159:80];
    assign w_col_2 = w_reg[383:256];
    assign idx_col_2 = idx_reg[239:160];
    assign w_col_3 = w_reg[511:384];
    assign idx_col_3 = idx_reg[319:240];
    assign w_col_4 = w_reg[639:512];
    assign idx_col_4 = idx_reg[399:320];
    assign w_col_5 = w_reg[767:640];
    assign idx_col_5 = idx_reg[479:400];
    assign w_col_6 = w_reg[895:768];
    assign idx_col_6 = idx_reg[559:480];
    assign w_col_7 = w_reg[1023:896];
    assign idx_col_7 = idx_reg[639:560];
    assign w_col_8 = w_reg[1151:1024];
    assign idx_col_8 = idx_reg[719:640];
    assign w_col_9 = w_reg[1279:1152];
    assign idx_col_9 = idx_reg[799:720];
    assign w_col_10 = w_reg[1407:1280];
    assign idx_col_10 = idx_reg[879:800];
    assign w_col_11 = w_reg[1535:1408];
    assign idx_col_11 = idx_reg[959:880];
    assign w_col_12 = w_reg[1663:1536];
    assign idx_col_12 = idx_reg[1039:960];
    assign w_col_13 = w_reg[1791:1664];
    assign idx_col_13 = idx_reg[1119:1040];
    assign w_col_14 = w_reg[1919:1792];
    assign idx_col_14 = idx_reg[1199:1120];
    assign w_col_15 = w_reg[2047:1920];
    assign idx_col_15 = idx_reg[1279:1200];

    always @(*) begin
        for (integer i = 0; i < 16; i = i + 1) begin
            c_vec[i] = 0;
            k_vec[i] = 0;
            case (max_k)
                1: begin
                    c_vec[i] = (p1_base_c + i);
                    k_vec[i] = 0;
                end
                2: begin
                    c_vec[i] = (p1_base_c + (i >> 1));
                    k_vec[i] = (i & 1);
                end
                4: begin
                    c_vec[i] = (p1_base_c + (i >> 2));
                    k_vec[i] = (i & 3);
                end
                8: begin
                    c_vec[i] = (p1_base_c + (i >> 3));
                    k_vec[i] = (i & 7);
                end
                default: begin
                    c_vec[i] = (p1_base_c + (i >> 4));
                    k_vec[i] = (i & 15);
                end
            endcase
        end
    end

    always @(*) begin
        for (integer i = 0; i < 16; i = i + 1) begin
            w_col_sel[i] = (c_vec[i][4] ? (c_vec[i][3] ? (c_vec[i][2] ? (c_vec[i][1] ? (c_vec[i][0] ? 0 : 0) : (c_vec[i][0] ? 0 : 0)) : (c_vec[i][1] ? (c_vec[i][0] ? 0 : 0) : (c_vec[i][0] ? 0 : 0))) : (c_vec[i][2] ? (c_vec[i][1] ? (c_vec[i][0] ? 0 : 0) : (c_vec[i][0] ? 0 : 0)) : (c_vec[i][1] ? (c_vec[i][0] ? 0 : 0) : (c_vec[i][0] ? 0 : 0)))) : (c_vec[i][3] ? (c_vec[i][2] ? (c_vec[i][1] ? (c_vec[i][0] ? w_col_15 : w_col_14) : (c_vec[i][0] ? w_col_13 : w_col_12)) : (c_vec[i][1] ? (c_vec[i][0] ? w_col_11 : w_col_10) : (c_vec[i][0] ? w_col_9 : w_col_8))) : (c_vec[i][2] ? (c_vec[i][1] ? (c_vec[i][0] ? w_col_7 : w_col_6) : (c_vec[i][0] ? w_col_5 : w_col_4)) : (c_vec[i][1] ? (c_vec[i][0] ? w_col_3 : w_col_2) : (c_vec[i][0] ? w_col_1 : w_col_0)))));
            idx_col_sel[i] = (c_vec[i][4] ? (c_vec[i][3] ? (c_vec[i][2] ? (c_vec[i][1] ? (c_vec[i][0] ? 0 : 0) : (c_vec[i][0] ? 0 : 0)) : (c_vec[i][1] ? (c_vec[i][0] ? 0 : 0) : (c_vec[i][0] ? 0 : 0))) : (c_vec[i][2] ? (c_vec[i][1] ? (c_vec[i][0] ? 0 : 0) : (c_vec[i][0] ? 0 : 0)) : (c_vec[i][1] ? (c_vec[i][0] ? 0 : 0) : (c_vec[i][0] ? 0 : 0)))) : (c_vec[i][3] ? (c_vec[i][2] ? (c_vec[i][1] ? (c_vec[i][0] ? idx_col_15 : idx_col_14) : (c_vec[i][0] ? idx_col_13 : idx_col_12)) : (c_vec[i][1] ? (c_vec[i][0] ? idx_col_11 : idx_col_10) : (c_vec[i][0] ? idx_col_9 : idx_col_8))) : (c_vec[i][2] ? (c_vec[i][1] ? (c_vec[i][0] ? idx_col_7 : idx_col_6) : (c_vec[i][0] ? idx_col_5 : idx_col_4)) : (c_vec[i][1] ? (c_vec[i][0] ? idx_col_3 : idx_col_2) : (c_vec[i][0] ? idx_col_1 : idx_col_0)))));
            w_val_vec_arr[i] = (k_vec[i][4] ? (k_vec[i][3] ? (k_vec[i][2] ? (k_vec[i][1] ? (k_vec[i][0] ? 0 : 0) : (k_vec[i][0] ? 0 : 0)) : (k_vec[i][1] ? (k_vec[i][0] ? 0 : 0) : (k_vec[i][0] ? 0 : 0))) : (k_vec[i][2] ? (k_vec[i][1] ? (k_vec[i][0] ? 0 : 0) : (k_vec[i][0] ? 0 : 0)) : (k_vec[i][1] ? (k_vec[i][0] ? 0 : 0) : (k_vec[i][0] ? 0 : 0)))) : (k_vec[i][3] ? (k_vec[i][2] ? (k_vec[i][1] ? (k_vec[i][0] ? w_col_sel[i][127:120] : w_col_sel[i][119:112]) : (k_vec[i][0] ? w_col_sel[i][111:104] : w_col_sel[i][103:96])) : (k_vec[i][1] ? (k_vec[i][0] ? w_col_sel[i][95:88] : w_col_sel[i][87:80]) : (k_vec[i][0] ? w_col_sel[i][79:72] : w_col_sel[i][71:64]))) : (k_vec[i][2] ? (k_vec[i][1] ? (k_vec[i][0] ? w_col_sel[i][63:56] : w_col_sel[i][55:48]) : (k_vec[i][0] ? w_col_sel[i][47:40] : w_col_sel[i][39:32])) : (k_vec[i][1] ? (k_vec[i][0] ? w_col_sel[i][31:24] : w_col_sel[i][23:16]) : (k_vec[i][0] ? w_col_sel[i][15:8] : w_col_sel[i][7:0])))));
            w_row_vec_arr[i] = (k_vec[i][4] ? (k_vec[i][3] ? (k_vec[i][2] ? (k_vec[i][1] ? (k_vec[i][0] ? 0 : 0) : (k_vec[i][0] ? 0 : 0)) : (k_vec[i][1] ? (k_vec[i][0] ? 0 : 0) : (k_vec[i][0] ? 0 : 0))) : (k_vec[i][2] ? (k_vec[i][1] ? (k_vec[i][0] ? 0 : 0) : (k_vec[i][0] ? 0 : 0)) : (k_vec[i][1] ? (k_vec[i][0] ? 0 : 0) : (k_vec[i][0] ? 0 : 0)))) : (k_vec[i][3] ? (k_vec[i][2] ? (k_vec[i][1] ? (k_vec[i][0] ? idx_col_sel[i][79:75] : idx_col_sel[i][74:70]) : (k_vec[i][0] ? idx_col_sel[i][69:65] : idx_col_sel[i][64:60])) : (k_vec[i][1] ? (k_vec[i][0] ? idx_col_sel[i][59:55] : idx_col_sel[i][54:50]) : (k_vec[i][0] ? idx_col_sel[i][49:45] : idx_col_sel[i][44:40]))) : (k_vec[i][2] ? (k_vec[i][1] ? (k_vec[i][0] ? idx_col_sel[i][39:35] : idx_col_sel[i][34:30]) : (k_vec[i][0] ? idx_col_sel[i][29:25] : idx_col_sel[i][24:20])) : (k_vec[i][1] ? (k_vec[i][0] ? idx_col_sel[i][19:15] : idx_col_sel[i][14:10]) : (k_vec[i][0] ? idx_col_sel[i][9:5] : idx_col_sel[i][4:0])))));
            w_val_vec_flat[(i * 8) +: 8] = w_val_vec_arr[i];
            w_row_vec_flat[(i * 5) +: 5] = w_row_vec_arr[i];
            c_vec_flat[(i * 5) +: 5] = c_vec[i];
        end
    end

endmodule

module FSMMRowEngine #(parameter ROW_IDX = 0) (
    input clk,
    input rst_n,
    input [2047:0] f_reg,
    input [127:0] w_val_vec_flat,
    input [79:0] w_row_vec_flat,
    input [79:0] c_vec_flat,
    input p1_valid,
    input p2_valid,
    input [4:0] p2_base_c,
    input [4:0] batch_cols,
    input [4:0] max_k,
    input [2047:0] out_buf,
    output reg [127:0] out_buf_next_row
);

    logic [127:0] f_row;
    logic [127:0] out_row;
    logic [7:0] w_val_vec [0:15];
    logic [4:0] w_row_vec [0:15];
    logic [4:0] c_vec [0:15];
    logic [7:0] f_val_vec [0:15];
    logic [15:0] mul_wire [0:15];
    reg [15:0] mul_reg [0:15];
    logic [15:0] p2_sum [0:15];
    logic [7:0] obn_elem [0:15];

    assign f_row = f_reg[((ROW_IDX * 16) * 8) +: 128];
    assign out_row = out_buf[((ROW_IDX * 16) * 8) +: 128];

    always @(*) begin
        for (integer i = 0; i < 16; i = i + 1) begin
            w_val_vec[i] = w_val_vec_flat[(i * 8) +: 8];
            w_row_vec[i] = w_row_vec_flat[(i * 5) +: 5];
            c_vec[i] = c_vec_flat[(i * 5) +: 5];
        end
    end

    always @(*) begin
        for (integer i = 0; i < 16; i = i + 1) begin
            f_val_vec[i] = (w_row_vec[i][4] ? (w_row_vec[i][3] ? (w_row_vec[i][2] ? (w_row_vec[i][1] ? (w_row_vec[i][0] ? 0 : 0) : (w_row_vec[i][0] ? 0 : 0)) : (w_row_vec[i][1] ? (w_row_vec[i][0] ? 0 : 0) : (w_row_vec[i][0] ? 0 : 0))) : (w_row_vec[i][2] ? (w_row_vec[i][1] ? (w_row_vec[i][0] ? 0 : 0) : (w_row_vec[i][0] ? 0 : 0)) : (w_row_vec[i][1] ? (w_row_vec[i][0] ? 0 : 0) : (w_row_vec[i][0] ? 0 : 0)))) : (w_row_vec[i][3] ? (w_row_vec[i][2] ? (w_row_vec[i][1] ? (w_row_vec[i][0] ? f_row[127:120] : f_row[119:112]) : (w_row_vec[i][0] ? f_row[111:104] : f_row[103:96])) : (w_row_vec[i][1] ? (w_row_vec[i][0] ? f_row[95:88] : f_row[87:80]) : (w_row_vec[i][0] ? f_row[79:72] : f_row[71:64]))) : (w_row_vec[i][2] ? (w_row_vec[i][1] ? (w_row_vec[i][0] ? f_row[63:56] : f_row[55:48]) : (w_row_vec[i][0] ? f_row[47:40] : f_row[39:32])) : (w_row_vec[i][1] ? (w_row_vec[i][0] ? f_row[31:24] : f_row[23:16]) : (w_row_vec[i][0] ? f_row[15:8] : f_row[7:0])))));
        end
    end

    always @(*) begin
        for (integer i = 0; i < 16; i = i + 1) begin
            mul_wire[i] = 0;
            if (p1_valid) begin
                if ((c_vec[i] < 16)) begin
                    mul_wire[i] = (f_val_vec[i] * w_val_vec[i]);
                end else begin
                end
            end else begin
            end
        end
    end

    always @(*) begin
        for (integer j = 0; j < 16; j = j + 1) begin
            p2_sum[j] = 0;
        end
        if (p2_valid) begin
            for (integer j = 0; j < 16; j = j + 1) begin
                if (((p2_base_c + j) < 16)) begin
                    p2s = 0;
                    case (max_k)
                        1: begin
                            p2s = mul_reg[j];
                        end
                        2: begin
                            if ((j < 8)) begin
                                p2s = (mul_reg[((j * 2) + 0)] + mul_reg[((j * 2) + 1)]);
                            end else begin
                            end
                        end
                        4: begin
                            if ((j < 4)) begin
                                p2s = (((mul_reg[((j * 4) + 0)] + mul_reg[((j * 4) + 1)]) + mul_reg[((j * 4) + 2)]) + mul_reg[((j * 4) + 3)]);
                            end else begin
                            end
                        end
                        8: begin
                            if ((j < 2)) begin
                                p2s = (((((((mul_reg[((j * 8) + 0)] + mul_reg[((j * 8) + 1)]) + mul_reg[((j * 8) + 2)]) + mul_reg[((j * 8) + 3)]) + mul_reg[((j * 8) + 4)]) + mul_reg[((j * 8) + 5)]) + mul_reg[((j * 8) + 6)]) + mul_reg[((j * 8) + 7)]);
                            end else begin
                            end
                        end
                        default: begin
                            if ((j < 1)) begin
                                p2s = ((((((mul_reg[((j * 16) + 0)] + mul_reg[((j * 16) + 1)]) + mul_reg[((j * 16) + 2)]) + mul_reg[((j * 16) + 3)]) + (((mul_reg[((j * 16) + 4)] + mul_reg[((j * 16) + 5)]) + mul_reg[((j * 16) + 6)]) + mul_reg[((j * 16) + 7)])) + (((mul_reg[((j * 16) + 8)] + mul_reg[((j * 16) + 9)]) + mul_reg[((j * 16) + 10)]) + mul_reg[((j * 16) + 11)])) + (((mul_reg[((j * 16) + 12)] + mul_reg[((j * 16) + 13)]) + mul_reg[((j * 16) + 14)]) + mul_reg[((j * 16) + 15)]));
                            end else begin
                            end
                        end
                    endcase
                    p2_sum[j] = p2s;
                end else begin
                end
            end
        end else begin
        end
    end

    always @(*) begin
        for (integer c = 0; c < 16; c = c + 1) begin
            obn_elem[c] = out_row[(c * 8) +: 8];
            if (p2_valid) begin
                if (((c >= p2_base_c) & (c < (p2_base_c + batch_cols)))) begin
                    case ((c - p2_base_c))
                        0: begin
                            obn_elem[c] = p2_sum[0][7:0];
                        end
                        1: begin
                            obn_elem[c] = p2_sum[1][7:0];
                        end
                        2: begin
                            obn_elem[c] = p2_sum[2][7:0];
                        end
                        3: begin
                            obn_elem[c] = p2_sum[3][7:0];
                        end
                        4: begin
                            obn_elem[c] = p2_sum[4][7:0];
                        end
                        5: begin
                            obn_elem[c] = p2_sum[5][7:0];
                        end
                        6: begin
                            obn_elem[c] = p2_sum[6][7:0];
                        end
                        7: begin
                            obn_elem[c] = p2_sum[7][7:0];
                        end
                        8: begin
                            obn_elem[c] = p2_sum[8][7:0];
                        end
                        9: begin
                            obn_elem[c] = p2_sum[9][7:0];
                        end
                        10: begin
                            obn_elem[c] = p2_sum[10][7:0];
                        end
                        11: begin
                            obn_elem[c] = p2_sum[11][7:0];
                        end
                        12: begin
                            obn_elem[c] = p2_sum[12][7:0];
                        end
                        13: begin
                            obn_elem[c] = p2_sum[13][7:0];
                        end
                        14: begin
                            obn_elem[c] = p2_sum[14][7:0];
                        end
                        15: begin
                            obn_elem[c] = p2_sum[15][7:0];
                        end
                        default: begin
                        end
                    endcase
                end else begin
                end
            end else begin
            end
        end
        out_buf_next_row = {obn_elem[15], obn_elem[14], obn_elem[13], obn_elem[12], obn_elem[11], obn_elem[10], obn_elem[9], obn_elem[8], obn_elem[7], obn_elem[6], obn_elem[5], obn_elem[4], obn_elem[3], obn_elem[2], obn_elem[1], obn_elem[0]};
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            for (integer i = 0; i < 16; i = i + 1) begin
                mul_reg[i] <= 0;
            end
        end else begin
            for (integer i = 0; i < 16; i = i + 1) begin
                mul_reg[i] <= mul_wire[i];
            end
        end
    end

endmodule

module FSMMDrRowEngine #(parameter ROW_IDX = 0) (
    input [2047:0] out_acc_buf,
    input [2047:0] out_buf,
    input [79:0] reorder_reg,
    input dr_cnt,
    input dr_en,
    output reg [127:0] out_acc_buf_next_row
);

    logic [127:0] out_acc_row;
    logic [127:0] out_row;
    logic [7:0] dr_add_val [0:7];
    logic [7:0] acc_elem [0:15];

    assign out_acc_row = out_acc_buf[((ROW_IDX * 16) * 8) +: 128];
    assign out_row = out_buf[((ROW_IDX * 16) * 8) +: 128];

    always @(*) begin
        for (integer j = 0; j < 8; j = j + 1) begin
            dr_add_val[j] = (dr_cnt ? out_row[((j + 8) * 8) +: 8] : out_row[(j * 8) +: 8]);
        end
    end

    always @(*) begin
        for (integer dst = 0; dst < 16; dst = dst + 1) begin
            acc_elem[dst] = out_acc_row[(dst * 8) +: 8];
            if (dr_en) begin
                acc_elem[dst] = (acc_elem[dst] + (((((reorder_reg[(dst * 5) +: 5] == ((dr_cnt * 8) + 0)) ? dr_add_val[0] : 0) + ((reorder_reg[(dst * 5) +: 5] == ((dr_cnt * 8) + 1)) ? dr_add_val[1] : 0)) + (((reorder_reg[(dst * 5) +: 5] == ((dr_cnt * 8) + 2)) ? dr_add_val[2] : 0) + ((reorder_reg[(dst * 5) +: 5] == ((dr_cnt * 8) + 3)) ? dr_add_val[3] : 0))) + ((((reorder_reg[(dst * 5) +: 5] == ((dr_cnt * 8) + 4)) ? dr_add_val[4] : 0) + ((reorder_reg[(dst * 5) +: 5] == ((dr_cnt * 8) + 5)) ? dr_add_val[5] : 0)) + (((reorder_reg[(dst * 5) +: 5] == ((dr_cnt * 8) + 6)) ? dr_add_val[6] : 0) + ((reorder_reg[(dst * 5) +: 5] == ((dr_cnt * 8) + 7)) ? dr_add_val[7] : 0)))));
            end else begin
            end
        end
        out_acc_buf_next_row = {acc_elem[15], acc_elem[14], acc_elem[13], acc_elem[12], acc_elem[11], acc_elem[10], acc_elem[9], acc_elem[8], acc_elem[7], acc_elem[6], acc_elem[5], acc_elem[4], acc_elem[3], acc_elem[2], acc_elem[1], acc_elem[0]};
    end

endmodule

module FSMM (
    input clk,
    input rst_n,
    input start,
    input [2:0] mode,
    input [2047:0] f_data,
    input [2047:0] w_data,
    input [1279:0] w_idx,
    input [79:0] reorder_idx,
    output valid_out,
    output [2047:0] o_data,
    output busy
);

    localparam STATE_IDLE = 0;
    localparam STATE_LOAD = 1;
    localparam STATE_COMPUTE = 2;
    localparam STATE_DEREORDER = 3;
    localparam STATE_OUTPUT = 4;

    logic [4:0] max_k;
    logic [4:0] batch_cols;
    logic dr_en;
    logic [127:0] fetch_w_val_vec_flat;
    logic [79:0] fetch_w_row_vec_flat;
    logic [79:0] fetch_c_vec_flat;
    reg [2047:0] f_reg;
    reg [2047:0] w_reg;
    reg [1279:0] idx_reg;
    reg [79:0] reorder_reg;
    reg [2:0] mode_reg;
    reg [2:0] state;
    reg [5:0] compute_cnt;
    reg [2047:0] out_buf;
    reg [2047:0] out_acc_buf;
    reg [2047:0] out_reg;
    reg valid_reg;
    reg [4:0] p1_base_c;
    reg p1_valid;
    reg [4:0] p2_base_c;
    reg p2_valid;
    reg dr_cnt;
    logic [127:0] out_buf_next_arr [0:15];
    logic [127:0] out_acc_buf_next_arr [0:15];

    FSMMFetchUnit u_fetch (
        .w_reg(w_reg),
        .idx_reg(idx_reg),
        .p1_base_c(p1_base_c),
        .max_k(max_k),
        .w_val_vec_flat(fetch_w_val_vec_flat),
        .w_row_vec_flat(fetch_w_row_vec_flat),
        .c_vec_flat(fetch_c_vec_flat)
    );

    generate
        genvar r;
        for (r = 0; r < 16; r = r + 1) begin : genblk
            FSMMRowEngine #(.ROW_IDX(r)) u_row (
                .clk(clk),
                .rst_n(rst_n),
                .f_reg(f_reg),
                .w_val_vec_flat(fetch_w_val_vec_flat),
                .w_row_vec_flat(fetch_w_row_vec_flat),
                .c_vec_flat(fetch_c_vec_flat),
                .p1_valid(p1_valid),
                .p2_valid(p2_valid),
                .p2_base_c(p2_base_c),
                .batch_cols(batch_cols),
                .max_k(max_k),
                .out_buf(out_buf),
                .out_buf_next_row(out_buf_next_arr[r])
            );

            FSMMDrRowEngine #(.ROW_IDX(r)) u_dr (
                .out_acc_buf(out_acc_buf),
                .out_buf(out_buf),
                .reorder_reg(reorder_reg),
                .dr_cnt(dr_cnt),
                .dr_en(dr_en),
                .out_acc_buf_next_row(out_acc_buf_next_arr[r])
            );

        end
    endgenerate
    always @(*) begin
        case (mode_reg)
            0: begin
                max_k = 1;
            end
            1: begin
                max_k = 2;
            end
            2: begin
                max_k = 4;
            end
            3: begin
                max_k = 8;
            end
            default: begin
                max_k = 16;
            end
        endcase
    end

    always @(*) begin
        case (max_k)
            1: begin
                batch_cols = 16;
            end
            2: begin
                batch_cols = 8;
            end
            4: begin
                batch_cols = 4;
            end
            8: begin
                batch_cols = 2;
            end
            default: begin
                batch_cols = 1;
            end
        endcase
    end

    assign dr_en = (state == STATE_DEREORDER);

    assign valid_out = valid_reg;
    assign o_data = out_reg;
    assign busy = ((state != STATE_IDLE) & (state != STATE_OUTPUT));

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            state <= STATE_IDLE;
            compute_cnt <= 0;
            valid_reg <= 0;
            out_buf <= 0;
            out_acc_buf <= 0;
            out_reg <= 0;
            f_reg <= 0;
            w_reg <= 0;
            idx_reg <= 0;
            reorder_reg <= 0;
            mode_reg <= 0;
            p1_valid <= 0;
            p2_valid <= 0;
            dr_cnt <= 0;
        end else begin
            case (state)
                STATE_IDLE: begin
                    valid_reg <= 0;
                    dr_cnt <= 0;
                    if (start) begin
                        f_reg <= f_data;
                        w_reg <= w_data;
                        idx_reg <= w_idx;
                        reorder_reg <= reorder_idx;
                        mode_reg <= mode;
                        state <= STATE_LOAD;
                    end
                end
                STATE_LOAD: begin
                    compute_cnt <= 0;
                    out_buf <= 0;
                    out_acc_buf <= 0;
                    p1_valid <= 0;
                    p2_valid <= 0;
                    state <= STATE_COMPUTE;
                end
                STATE_COMPUTE: begin
                    if ((compute_cnt < max_k)) begin
                        p1_valid <= 1;
                        p1_base_c <= (compute_cnt * batch_cols);
                        compute_cnt <= (compute_cnt + 1);
                    end else begin
                        p1_valid <= 0;
                    end
                    p2_valid <= p1_valid;
                    p2_base_c <= p1_base_c;
                    out_buf <= {out_buf_next_arr[15], out_buf_next_arr[14], out_buf_next_arr[13], out_buf_next_arr[12], out_buf_next_arr[11], out_buf_next_arr[10], out_buf_next_arr[9], out_buf_next_arr[8], out_buf_next_arr[7], out_buf_next_arr[6], out_buf_next_arr[5], out_buf_next_arr[4], out_buf_next_arr[3], out_buf_next_arr[2], out_buf_next_arr[1], out_buf_next_arr[0]};
                    if ((((compute_cnt >= max_k) & (p1_valid == 0)) & (p2_valid == 0))) begin
                        state <= STATE_DEREORDER;
                    end
                end
                STATE_DEREORDER: begin
                    out_acc_buf <= {out_acc_buf_next_arr[15], out_acc_buf_next_arr[14], out_acc_buf_next_arr[13], out_acc_buf_next_arr[12], out_acc_buf_next_arr[11], out_acc_buf_next_arr[10], out_acc_buf_next_arr[9], out_acc_buf_next_arr[8], out_acc_buf_next_arr[7], out_acc_buf_next_arr[6], out_acc_buf_next_arr[5], out_acc_buf_next_arr[4], out_acc_buf_next_arr[3], out_acc_buf_next_arr[2], out_acc_buf_next_arr[1], out_acc_buf_next_arr[0]};
                    dr_cnt <= (dr_cnt + 1);
                    if ((dr_cnt == 1)) begin
                        state <= STATE_OUTPUT;
                    end
                end
                STATE_OUTPUT: begin
                    out_reg <= out_acc_buf;
                    valid_reg <= 1;
                    state <= STATE_IDLE;
                end
                default: begin
                    state <= STATE_IDLE;
                end
            endcase
        end
    end

endmodule
