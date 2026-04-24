`default_nettype none
module FP16FP8SharedALU (
    input clk,
    input rst_n,
    input i_valid,
    input [15:0] a,
    input [15:0] b,
    input [2:0] op,
    input fmt,
    input o_ready,
    output i_ready,
    output o_valid,
    output [15:0] result,
    output [3:0] flags
);

    logic a_sign_fp8;
    logic [4:0] a_exp_fp8;
    logic [1:0] a_mant_fp8;
    logic a_hidden_fp8;
    logic [10:0] a_mant_full_fp8;
    logic b_sign_fp8;
    logic [4:0] b_exp_fp8;
    logic [1:0] b_mant_fp8;
    logic b_hidden_fp8;
    logic [10:0] b_mant_full_fp8;
    logic a_sign_fp16;
    logic [4:0] a_exp_fp16;
    logic [9:0] a_mant_fp16;
    logic a_hidden_fp16;
    logic [10:0] a_mant_full_fp16;
    logic b_sign_fp16;
    logic [4:0] b_exp_fp16;
    logic [9:0] b_mant_fp16;
    logic b_hidden_fp16;
    logic [10:0] b_mant_full_fp16;
    logic a_sign;
    logic [4:0] a_exp;
    logic [10:0] a_mant_full;
    logic a_is_nan;
    logic a_is_inf;
    logic a_is_zero;
    logic [14:0] a_mag;
    logic b_sign;
    logic [4:0] b_exp;
    logic [10:0] b_mant_full;
    logic b_is_nan;
    logic b_is_inf;
    logic b_is_zero;
    logic [14:0] b_mag;
    logic s1_ready;
    logic s2_ready;
    logic s3_ready;
    logic add_eff_b_sign;
    logic add_a_is_bigger;
    logic [4:0] add_big_exp;
    logic add_big_sign;
    logic [10:0] add_big_mant;
    logic add_small_sign;
    logic [10:0] add_small_mant;
    logic [4:0] add_shift;
    logic [13:0] add_small_mant_shifted;
    logic [15:0] add_big_mant_ext;
    logic [15:0] add_small_mant_ext;
    logic [15:0] add_signed_big;
    logic [15:0] add_signed_small;
    logic [16:0] add_raw_sum;
    logic add_res_sign;
    logic [16:0] add_res_mag;
    logic [3:0] add_norm_shift;
    logic [31:0] add_norm_shifted;
    logic [10:0] add_norm_mant;
    logic [6:0] add_norm_exp;
    logic mul_sign;
    logic [4:0] mul_a_eff_exp;
    logic [4:0] mul_b_eff_exp;
    logic [6:0] mul_exp_raw;
    logic [21:0] mul_prod;
    logic mul_ovf;
    logic [21:0] mul_norm_prod;
    logic mul_guard;
    logic [11:0] mul_mant_tmp;
    logic mul_mant_ovf;
    logic [10:0] mul_mant;
    logic [6:0] mul_exp;
    logic cmp_lt;
    logic cmp_eq;
    logic minmax_sel_a;
    logic s2_res_sign_in;
    logic [6:0] s2_res_exp_in;
    logic [10:0] s2_res_mant_in;
    logic s2_is_nan_in;
    logic s2_is_inf_in;
    logic s2_is_zero_in;
    logic s2_cmp_lt_in;
    logic s2_cmp_eq_in;
    logic s2_minmax_sel_a_in;
    logic [15:0] arith_result_fp16;
    logic [7:0] arith_result_fp8;
    logic [15:0] arith_result;
    logic [15:0] cmp_result;
    logic [15:0] minmax_result;
    logic [15:0] final_result;
    logic [3:0] final_flags;
    logic [2:0] fp8_mant_top3;
    logic [7:0] fp8_mant_lower;
    logic [3:0] fp8_rounded_mant3;
    logic [6:0] fp8_rounded_exp;
    logic [4:0] fp8_pack_exp;
    logic [1:0] fp8_pack_mant;
    reg s1_valid;
    reg s1_a_sign;
    reg [4:0] s1_a_exp;
    reg [10:0] s1_a_mant_full;
    reg s1_a_is_nan;
    reg s1_a_is_inf;
    reg s1_a_is_zero;
    reg [14:0] s1_a_mag;
    reg s1_b_sign;
    reg [4:0] s1_b_exp;
    reg [10:0] s1_b_mant_full;
    reg s1_b_is_nan;
    reg s1_b_is_inf;
    reg s1_b_is_zero;
    reg [14:0] s1_b_mag;
    reg [2:0] s1_op;
    reg s1_fmt;
    reg s2_valid;
    reg o_valid_reg;
    reg s2_res_sign;
    reg [6:0] s2_res_exp;
    reg [10:0] s2_res_mant;
    reg s2_is_nan;
    reg s2_is_inf;
    reg s2_is_zero;
    reg [2:0] s2_op;
    reg s2_fmt;
    reg s2_cmp_lt;
    reg s2_cmp_eq;
    reg s2_minmax_sel_a;
    reg [15:0] s2_minmax_a;
    reg [15:0] s2_minmax_b;
    reg [15:0] s1_a_raw;
    reg [15:0] s1_b_raw;
    reg [15:0] result_reg;
    reg [3:0] flags_reg;

    assign s1_ready = ((~s1_valid) | s2_ready);
    assign s2_ready = ((~s2_valid) | s3_ready);
    assign s3_ready = ((~o_valid_reg) | o_ready);
    assign i_ready = s1_ready;
    always @(*) begin
        a_sign_fp8 = a[7];
        a_exp_fp8 = a[6:2];
        a_mant_fp8 = a[1:0];
        case (a_exp_fp8)
            0: a_hidden_fp8 = 1'd0;
            default: a_hidden_fp8 = 1'd1;
        endcase
        a_mant_full_fp8 = {a_hidden_fp8, a_mant_fp8, 8'd0};
        b_sign_fp8 = b[7];
        b_exp_fp8 = b[6:2];
        b_mant_fp8 = b[1:0];
        case (b_exp_fp8)
            0: b_hidden_fp8 = 1'd0;
            default: b_hidden_fp8 = 1'd1;
        endcase
        b_mant_full_fp8 = {b_hidden_fp8, b_mant_fp8, 8'd0};
        a_sign_fp16 = a[15];
        a_exp_fp16 = a[14:10];
        a_mant_fp16 = a[9:0];
        case (a_exp_fp16)
            0: a_hidden_fp16 = 1'd0;
            default: a_hidden_fp16 = 1'd1;
        endcase
        a_mant_full_fp16 = {a_hidden_fp16, a_mant_fp16};
        b_sign_fp16 = b[15];
        b_exp_fp16 = b[14:10];
        b_mant_fp16 = b[9:0];
        case (b_exp_fp16)
            0: b_hidden_fp16 = 1'd0;
            default: b_hidden_fp16 = 1'd1;
        endcase
        b_mant_full_fp16 = {b_hidden_fp16, b_mant_fp16};
        a_sign = (fmt ? a_sign_fp16 : a_sign_fp8);
        a_exp = (fmt ? a_exp_fp16 : a_exp_fp8);
        a_mant_full = (fmt ? a_mant_full_fp16 : a_mant_full_fp8);
        a_is_nan = (fmt ? ((a_exp_fp16 == 5'd31) & (a_mant_fp16 != 1'd0)) : ((a_exp_fp8 == 5'd31) & (a_mant_fp8 != 1'd0)));
        a_is_inf = (fmt ? ((a_exp_fp16 == 5'd31) & (a_mant_fp16 == 1'd0)) : ((a_exp_fp8 == 5'd31) & (a_mant_fp8 == 1'd0)));
        a_is_zero = (fmt ? ((a_exp_fp16 == 1'd0) & (a_mant_fp16 == 1'd0)) : ((a_exp_fp8 == 1'd0) & (a_mant_fp8 == 1'd0)));
        a_mag = {a_exp, (fmt ? a_mant_fp16 : {a_mant_fp8, 8'd0})};
        b_sign = (fmt ? b_sign_fp16 : b_sign_fp8);
        b_exp = (fmt ? b_exp_fp16 : b_exp_fp8);
        b_mant_full = (fmt ? b_mant_full_fp16 : b_mant_full_fp8);
        b_is_nan = (fmt ? ((b_exp_fp16 == 5'd31) & (b_mant_fp16 != 1'd0)) : ((b_exp_fp8 == 5'd31) & (b_mant_fp8 != 1'd0)));
        b_is_inf = (fmt ? ((b_exp_fp16 == 5'd31) & (b_mant_fp16 == 1'd0)) : ((b_exp_fp8 == 5'd31) & (b_mant_fp8 == 1'd0)));
        b_is_zero = (fmt ? ((b_exp_fp16 == 1'd0) & (b_mant_fp16 == 1'd0)) : ((b_exp_fp8 == 1'd0) & (b_mant_fp8 == 1'd0)));
        b_mag = {b_exp, (fmt ? b_mant_fp16 : {b_mant_fp8, 8'd0})};
    end

    always @(*) begin
        cmp_eq = 1'b0;
        cmp_lt = 1'b0;
        minmax_sel_a = 1'b0;
        s1_a_sign = 1'b0;
        add_eff_b_sign = ((s1_op == 1'd1) ? (s1_b_sign ^ 1'd1) : s1_b_sign);
        add_a_is_bigger = ((s1_a_exp > s1_b_exp) | ((s1_a_exp == s1_b_exp) & (s1_a_mant_full >= s1_b_mant_full)));
        add_big_exp = (add_a_is_bigger ? s1_a_exp : s1_b_exp);
        add_big_sign = (add_a_is_bigger ? s1_a_sign : add_eff_b_sign);
        add_big_mant = (add_a_is_bigger ? s1_a_mant_full : s1_b_mant_full);
        add_small_sign = (add_a_is_bigger ? add_eff_b_sign : s1_a_sign);
        add_small_mant = (add_a_is_bigger ? s1_b_mant_full : s1_a_mant_full);
        add_shift = (add_a_is_bigger ? (s1_a_exp - s1_b_exp) : (s1_b_exp - s1_a_exp));
        add_small_mant_shifted = ({add_small_mant, 3'd0} >> add_shift);
        add_big_mant_ext = {2'd0, add_big_mant, 3'd0};
        add_small_mant_ext = {2'd0, add_small_mant_shifted};
        add_signed_big = (add_big_sign ? (16'd0 - add_big_mant_ext) : add_big_mant_ext);
        add_signed_small = (add_small_sign ? (16'd0 - add_small_mant_ext) : add_small_mant_ext);
        add_raw_sum = ({add_signed_big[15], add_signed_big} + {add_signed_small[15], add_signed_small});
        add_res_sign = add_raw_sum[16];
        add_res_mag = (add_res_sign ? (17'd0 - add_raw_sum) : add_raw_sum);
        add_norm_shift = (add_res_mag[14] ? 4'd0 : (add_res_mag[13] ? 4'd1 : (add_res_mag[12] ? 4'd2 : (add_res_mag[11] ? 4'd3 : (add_res_mag[10] ? 4'd4 : (add_res_mag[9] ? 4'd5 : (add_res_mag[8] ? 4'd6 : (add_res_mag[7] ? 4'd7 : (add_res_mag[6] ? 4'd8 : (add_res_mag[5] ? 4'd9 : (add_res_mag[4] ? 4'd10 : (add_res_mag[3] ? 4'd11 : (add_res_mag[2] ? 4'd12 : (add_res_mag[1] ? 4'd13 : (add_res_mag[0] ? 4'd14 : 4'd15)))))))))))))));
        add_norm_shifted = (add_res_mag << add_norm_shift);
        add_norm_mant = ((add_res_mag == 1'd0) ? 11'd0 : add_norm_shifted[14:4]);
        add_norm_exp = ((add_res_mag == 1'd0) ? 7'd0 : (({2'd0, add_big_exp} + 1'd1) - add_norm_shift));
        mul_sign = (s1_a_sign ^ s1_b_sign);
        mul_a_eff_exp = ((s1_a_exp == 1'd0) ? 1'd1 : s1_a_exp);
        mul_b_eff_exp = ((s1_b_exp == 1'd0) ? 1'd1 : s1_b_exp);
        mul_exp_raw = ((mul_a_eff_exp + mul_b_eff_exp) - 4'd15);
        mul_prod = (s1_a_mant_full * s1_b_mant_full);
        mul_ovf = mul_prod[21];
        mul_norm_prod = (mul_ovf ? (mul_prod >> 1'd1) : mul_prod);
        mul_guard = (mul_ovf ? mul_prod[0] : mul_prod[1]);
        mul_mant_tmp = (mul_norm_prod[20:10] + mul_guard);
        mul_mant_ovf = mul_mant_tmp[11];
        mul_mant = (mul_mant_ovf ? 11'd1024 : mul_mant_tmp[10:0]);
        mul_exp = ((mul_exp_raw + mul_ovf) + mul_mant_ovf);
        if ((s1_a_is_nan | s1_b_is_nan)) begin
            cmp_lt = 1'd0;
            cmp_eq = 1'd0;
            minmax_sel_a = (s1_b_is_nan ? 1'd1 : 1'd0);
        end else begin
            if ((s1_a_is_zero & s1_b_is_zero)) begin
                cmp_lt = 1'd0;
                cmp_eq = 1'd1;
                minmax_sel_a = 1'd0;
            end else begin
                if ((s1_a_sign != s1_b_sign)) begin
                    cmp_eq = 1'd0;
                    if ((s1_a_sign == 1'd1)) begin
                        cmp_lt = 1'd1;
                        minmax_sel_a = ((s1_op == 2'd3) ? 1'd1 : 1'd0);
                    end else begin
                        cmp_lt = 1'd0;
                        minmax_sel_a = ((s1_op == 2'd3) ? 1'd0 : 1'd1);
                    end
                end else begin
                    cmp_eq = (s1_a_mag == s1_b_mag);
                    if ((s1_a_sign == 1'd0)) begin
                        cmp_lt = (s1_a_mag < s1_b_mag);
                        minmax_sel_a = ((s1_op == 2'd3) ? (s1_a_mag < s1_b_mag) : (s1_a_mag > s1_b_mag));
                    end else begin
                        cmp_lt = (s1_a_mag > s1_b_mag);
                        minmax_sel_a = ((s1_op == 2'd3) ? (s1_a_mag > s1_b_mag) : (s1_a_mag < s1_b_mag));
                    end
                end
            end
        end
    end

    always @(*) begin
        case (s1_op)
            2: s2_res_sign_in = mul_sign;
            default: s2_res_sign_in = add_res_sign;
        endcase
        case (s1_op)
            2: s2_res_exp_in = mul_exp;
            default: s2_res_exp_in = add_norm_exp;
        endcase
        case (s1_op)
            2: s2_res_mant_in = mul_mant;
            default: s2_res_mant_in = add_norm_mant;
        endcase
        case (s1_op)
            2: s2_is_nan_in = (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf));
            default: s2_is_nan_in = ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 1'd0) | (s1_op == 1'd1))) & (s1_a_sign != add_eff_b_sign)));
        endcase
        case (s1_op)
            2: s2_is_inf_in = (((s1_a_is_inf | s1_b_is_inf) | ((mul_exp >= 5'd31) & (~mul_exp[6]))) & (~((s1_op == 2'd2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 1'd0) | (s1_op == 1'd1))) & (s1_a_sign != add_eff_b_sign))))));
            default: s2_is_inf_in = (((s1_a_is_inf | s1_b_is_inf) | ((add_norm_exp >= 5'd31) & (~add_norm_exp[6]))) & (~((s1_op == 2'd2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 1'd0) | (s1_op == 1'd1))) & (s1_a_sign != add_eff_b_sign))))));
        endcase
        s2_is_zero_in = ((((s1_op == 2'd2) ? (s1_a_is_zero | s1_b_is_zero) : ((add_res_mag == 1'd0) & ((s1_op == 1'd0) | (s1_op == 1'd1)))) & (~((s1_op == 2'd2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 1'd0) | (s1_op == 1'd1))) & (s1_a_sign != add_eff_b_sign)))))) & (~((s1_op == 2'd2) ? (((s1_a_is_inf | s1_b_is_inf) | ((mul_exp >= 5'd31) & (~mul_exp[6]))) & (~((s1_op == 2'd2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 1'd0) | (s1_op == 1'd1))) & (s1_a_sign != add_eff_b_sign)))))) : (((s1_a_is_inf | s1_b_is_inf) | ((add_norm_exp >= 5'd31) & (~add_norm_exp[6]))) & (~((s1_op == 2'd2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 1'd0) | (s1_op == 1'd1))) & (s1_a_sign != add_eff_b_sign)))))))));
        s2_cmp_lt_in = cmp_lt;
        s2_cmp_eq_in = cmp_eq;
        s2_minmax_sel_a_in = minmax_sel_a;
    end

    always @(*) begin
        if (s2_is_nan) begin
            arith_result_fp16 = {1'd0, 5'd31, 10'd1};
        end else begin
            if ((s2_is_inf | ((s2_res_exp >= 5'd31) & (~s2_res_exp[6])))) begin
                arith_result_fp16 = {s2_res_sign, 5'd31, 10'd0};
            end else begin
                if ((s2_is_zero | s2_res_exp[6])) begin
                    arith_result_fp16 = {s2_res_sign, 5'd0, 10'd0};
                end else begin
                    arith_result_fp16 = {s2_res_sign, s2_res_exp[4:0], s2_res_mant[9:0]};
                end
            end
        end
        fp8_mant_top3 = s2_res_mant[10:8];
        fp8_mant_lower = s2_res_mant[7:0];
        fp8_rounded_mant3 = ({1'd0, fp8_mant_top3} + ((fp8_mant_lower >= 8'd128) ? 1'd1 : 1'd0));
        fp8_rounded_exp = (s2_res_exp + (fp8_rounded_mant3[3] ? 1'd1 : 1'd0));
        fp8_pack_exp = (fp8_rounded_mant3[3] ? fp8_rounded_exp[4:0] : fp8_rounded_exp[4:0]);
        fp8_pack_mant = (fp8_rounded_mant3[3] ? 2'd0 : fp8_rounded_mant3[1:0]);
        if (s2_is_nan) begin
            arith_result_fp8 = {1'd0, 5'd31, 2'd1};
        end else begin
            if ((s2_is_inf | ((fp8_rounded_exp >= 5'd31) & (~fp8_rounded_exp[6])))) begin
                arith_result_fp8 = {s2_res_sign, 5'd31, 2'd0};
            end else begin
                if ((s2_is_zero | fp8_rounded_exp[6])) begin
                    arith_result_fp8 = {s2_res_sign, 5'd0, 2'd0};
                end else begin
                    arith_result_fp8 = {s2_res_sign, fp8_pack_exp, fp8_pack_mant};
                end
            end
        end
        arith_result = (s2_fmt ? arith_result_fp16 : {8'd0, arith_result_fp8});
        cmp_result = {15'd0, ((s2_op == 3'd5) ? s2_cmp_lt : s2_cmp_eq)};
        minmax_result = (s2_minmax_sel_a ? s2_minmax_a : s2_minmax_b);
        if (((s2_op == 3'd5) | (s2_op == 3'd6))) begin
            final_result = cmp_result;
        end else begin
            if (((s2_op == 2'd3) | (s2_op == 3'd4))) begin
                final_result = minmax_result;
            end else begin
                final_result = arith_result;
            end
        end
        final_flags = {(s2_is_nan & (((s2_op == 1'd0) | (s2_op == 1'd1)) | (s2_op == 2'd2))), ((s2_is_inf | ((fp8_rounded_mant3[3] & (~s2_fmt)) & (fp8_rounded_exp >= 5'd31))) & (((s2_op == 1'd0) | (s2_op == 1'd1)) | (s2_op == 2'd2))), (((s2_is_zero & (~(s2_is_nan & (((s2_op == 1'd0) | (s2_op == 1'd1)) | (s2_op == 2'd2))))) & (~((s2_is_inf | ((fp8_rounded_mant3[3] & (~s2_fmt)) & (fp8_rounded_exp >= 5'd31))) & (((s2_op == 1'd0) | (s2_op == 1'd1)) | (s2_op == 2'd2))))) & (((s2_op == 1'd0) | (s2_op == 1'd1)) | (s2_op == 2'd2))), 1'd0};
    end

    assign o_valid = o_valid_reg;
    assign result = (o_valid_reg ? result_reg : 16'd0);
    assign flags = (o_valid_reg ? flags_reg : 4'd0);

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 1'd0)) begin
            s1_valid <= 1'd0;
        end else begin
            if (s1_ready) begin
                s1_valid <= i_valid;
                if (i_valid) begin
                    s1_a_sign <= a_sign;
                    s1_a_exp <= a_exp;
                    s1_a_mant_full <= a_mant_full;
                    s1_a_is_nan <= a_is_nan;
                    s1_a_is_inf <= a_is_inf;
                    s1_a_is_zero <= a_is_zero;
                    s1_a_mag <= a_mag;
                    s1_b_sign <= b_sign;
                    s1_b_exp <= b_exp;
                    s1_b_mant_full <= b_mant_full;
                    s1_b_is_nan <= b_is_nan;
                    s1_b_is_inf <= b_is_inf;
                    s1_b_is_zero <= b_is_zero;
                    s1_b_mag <= b_mag;
                    s1_op <= op;
                    s1_fmt <= fmt;
                end
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 1'd0)) begin
        end else begin
            if ((s1_ready & i_valid)) begin
                s1_a_raw <= a;
                s1_b_raw <= b;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 1'd0)) begin
            s2_valid <= 1'd0;
        end else begin
            if (s2_ready) begin
                s2_valid <= s1_valid;
                if (s1_valid) begin
                    s2_res_sign <= s2_res_sign_in;
                    s2_res_exp <= s2_res_exp_in;
                    s2_res_mant <= s2_res_mant_in;
                    s2_is_nan <= s2_is_nan_in;
                    s2_is_inf <= s2_is_inf_in;
                    s2_is_zero <= s2_is_zero_in;
                    s2_op <= s1_op;
                    s2_fmt <= s1_fmt;
                    s2_cmp_lt <= s2_cmp_lt_in;
                    s2_cmp_eq <= s2_cmp_eq_in;
                    s2_minmax_sel_a <= s2_minmax_sel_a_in;
                    s2_minmax_a <= s1_a_raw;
                    s2_minmax_b <= s1_b_raw;
                end
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 1'd0)) begin
            o_valid_reg <= 1'd0;
        end else begin
            if (s3_ready) begin
                o_valid_reg <= s2_valid;
                if (s2_valid) begin
                    result_reg <= final_result;
                    flags_reg <= final_flags;
                end
            end
        end
    end

endmodule