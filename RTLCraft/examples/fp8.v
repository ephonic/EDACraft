module fp8e5m2_alu (
    input clk,
    input rst_n,
    input i_valid,
    input [7:0] a,
    input [7:0] b,
    input [2:0] op,
    input o_ready,
    output i_ready,
    output o_valid,
    output [7:0] result,
    output [3:0] flags
);

    logic a_sign;
    logic [4:0] a_exp;
    logic [1:0] a_mant;
    logic a_hidden;
    logic [2:0] a_mant_full;
    logic a_is_nan;
    logic a_is_inf;
    logic a_is_zero;
    logic [6:0] a_mag;
    logic b_sign;
    logic [4:0] b_exp;
    logic [1:0] b_mant;
    logic b_hidden;
    logic [2:0] b_mant_full;
    logic b_is_nan;
    logic b_is_inf;
    logic b_is_zero;
    logic [6:0] b_mag;
    logic s1_ready;
    logic s2_ready;
    logic s3_ready;
    logic add_eff_b_sign;
    logic add_a_is_bigger;
    logic [4:0] add_big_exp;
    logic add_big_sign;
    logic [2:0] add_big_mant;
    logic add_small_sign;
    logic [2:0] add_small_mant;
    logic [4:0] add_shift;
    logic [5:0] add_small_mant_shifted;
    logic [7:0] add_big_mant_ext;
    logic [7:0] add_small_mant_ext;
    logic [7:0] add_signed_big;
    logic [7:0] add_signed_small;
    logic [8:0] add_raw_sum;
    logic add_res_sign;
    logic [8:0] add_res_mag;
    logic [2:0] add_norm_mant;
    logic [6:0] add_norm_exp;
    logic mul_sign;
    logic [4:0] mul_a_eff_exp;
    logic [4:0] mul_b_eff_exp;
    logic [6:0] mul_exp_raw;
    logic [5:0] mul_prod;
    logic mul_ovf;
    logic [5:0] mul_norm_prod;
    logic mul_guard;
    logic [3:0] mul_mant_tmp;
    logic mul_mant_ovf;
    logic [2:0] mul_mant;
    logic [6:0] mul_exp;
    logic cmp_lt;
    logic cmp_eq;
    logic minmax_sel_a;
    logic s2_res_sign_in;
    logic [6:0] s2_res_exp_in;
    logic [2:0] s2_res_mant_in;
    logic s2_is_nan_in;
    logic s2_is_inf_in;
    logic s2_is_zero_in;
    logic s2_cmp_lt_in;
    logic s2_cmp_eq_in;
    logic s2_minmax_sel_a_in;
    logic [7:0] arith_result;
    logic [7:0] cmp_result;
    logic [7:0] minmax_result;
    logic [7:0] final_result;
    logic [3:0] final_flags;
    reg s1_valid;
    reg s1_a_sign;
    reg [4:0] s1_a_exp;
    reg [2:0] s1_a_mant_full;
    reg s1_a_is_nan;
    reg s1_a_is_inf;
    reg s1_a_is_zero;
    reg [6:0] s1_a_mag;
    reg s1_b_sign;
    reg [4:0] s1_b_exp;
    reg [2:0] s1_b_mant_full;
    reg s1_b_is_nan;
    reg s1_b_is_inf;
    reg s1_b_is_zero;
    reg [6:0] s1_b_mag;
    reg [2:0] s1_op;
    reg s2_valid;
    reg o_valid_reg;
    reg s2_res_sign;
    reg [6:0] s2_res_exp;
    reg [2:0] s2_res_mant;
    reg s2_is_nan;
    reg s2_is_inf;
    reg s2_is_zero;
    reg [2:0] s2_op;
    reg s2_cmp_lt;
    reg s2_cmp_eq;
    reg s2_minmax_sel_a;
    reg [7:0] s2_minmax_a;
    reg [7:0] s2_minmax_b;
    reg [7:0] s1_a_raw;
    reg [7:0] s1_b_raw;
    reg [7:0] result_reg;
    reg [3:0] flags_reg;

    assign s1_ready = ((~s1_valid) | s2_ready);
    assign s2_ready = ((~s2_valid) | s3_ready);
    assign s3_ready = ((~o_valid_reg) | o_ready);
    assign i_ready = s1_ready;
    always @(*) begin
        a_sign = a[7];
        a_exp = a[6:2];
        a_mant = a[1:0];
        case (a_exp)
            0: a_hidden = 0;
            default: a_hidden = 1;
        endcase
        a_mant_full = {a_hidden, a_mant};
        a_is_nan = ((a_exp == 31) & (a_mant != 0));
        a_is_inf = ((a_exp == 31) & (a_mant == 0));
        a_is_zero = ((a_exp == 0) & (a_mant == 0));
        a_mag = {a_exp, a_mant};
        b_sign = b[7];
        b_exp = b[6:2];
        b_mant = b[1:0];
        case (b_exp)
            0: b_hidden = 0;
            default: b_hidden = 1;
        endcase
        b_mant_full = {b_hidden, b_mant};
        b_is_nan = ((b_exp == 31) & (b_mant != 0));
        b_is_inf = ((b_exp == 31) & (b_mant == 0));
        b_is_zero = ((b_exp == 0) & (b_mant == 0));
        b_mag = {b_exp, b_mant};
    end

    always @(*) begin
        add_eff_b_sign = ((s1_op == 1) ? (s1_b_sign ^ 1) : s1_b_sign);
        add_a_is_bigger = ((s1_a_exp > s1_b_exp) | ((s1_a_exp == s1_b_exp) & (s1_a_mant_full >= s1_b_mant_full)));
        add_big_exp = (add_a_is_bigger ? s1_a_exp : s1_b_exp);
        add_big_sign = (add_a_is_bigger ? s1_a_sign : add_eff_b_sign);
        add_big_mant = (add_a_is_bigger ? s1_a_mant_full : s1_b_mant_full);
        add_small_sign = (add_a_is_bigger ? add_eff_b_sign : s1_a_sign);
        add_small_mant = (add_a_is_bigger ? s1_b_mant_full : s1_a_mant_full);
        add_shift = (add_a_is_bigger ? (s1_a_exp - s1_b_exp) : (s1_b_exp - s1_a_exp));
        add_small_mant_shifted = ({add_small_mant, 0} >> add_shift);
        add_big_mant_ext = {0, add_big_mant, 0};
        add_small_mant_ext = {0, add_small_mant_shifted};
        add_signed_big = (add_big_sign ? (0 - add_big_mant_ext) : add_big_mant_ext);
        add_signed_small = (add_small_sign ? (0 - add_small_mant_ext) : add_small_mant_ext);
        add_raw_sum = ({add_signed_big[7], add_signed_big} + {add_signed_small[7], add_signed_small});
        add_res_sign = add_raw_sum[8];
        add_res_mag = (add_res_sign ? (0 - add_raw_sum) : add_raw_sum);
        if (add_res_mag[6]) begin
            add_norm_mant = add_res_mag[6:4];
            add_norm_exp = ({0, add_big_exp} + 1);
        end else begin
            if (add_res_mag[5]) begin
                add_norm_mant = add_res_mag[5:3];
                add_norm_exp = {0, add_big_exp};
            end else begin
                if (add_res_mag[4]) begin
                    add_norm_mant = add_res_mag[4:2];
                    add_norm_exp = ({0, add_big_exp} - 1);
                end else begin
                    if (add_res_mag[3]) begin
                        add_norm_mant = add_res_mag[3:1];
                        add_norm_exp = ({0, add_big_exp} - 2);
                    end else begin
                        if (add_res_mag[2]) begin
                            add_norm_mant = add_res_mag[2:0];
                            add_norm_exp = ({0, add_big_exp} - 3);
                        end else begin
                            if (add_res_mag[1]) begin
                                add_norm_mant = {add_res_mag[1:0], 0};
                                add_norm_exp = ({0, add_big_exp} - 4);
                            end else begin
                                if (add_res_mag[0]) begin
                                    add_norm_mant = {add_res_mag[0], 0};
                                    add_norm_exp = ({0, add_big_exp} - 5);
                                end else begin
                                    add_norm_mant = 0;
                                    add_norm_exp = 0;
                                end
                            end
                        end
                    end
                end
            end
        end
        mul_sign = (s1_a_sign ^ s1_b_sign);
        mul_a_eff_exp = ((s1_a_exp == 0) ? 1 : s1_a_exp);
        mul_b_eff_exp = ((s1_b_exp == 0) ? 1 : s1_b_exp);
        mul_exp_raw = ((mul_a_eff_exp + mul_b_eff_exp) - 15);
        mul_prod = (s1_a_mant_full * s1_b_mant_full);
        mul_ovf = mul_prod[5];
        mul_norm_prod = (mul_ovf ? (mul_prod >> 1) : mul_prod);
        mul_guard = (mul_ovf ? mul_prod[0] : mul_prod[1]);
        mul_mant_tmp = (mul_norm_prod[4:2] + mul_guard);
        mul_mant_ovf = mul_mant_tmp[3];
        mul_mant = (mul_mant_ovf ? 4 : mul_mant_tmp[2:0]);
        mul_exp = ((mul_exp_raw + mul_ovf) + mul_mant_ovf);
        if ((s1_a_is_nan | s1_b_is_nan)) begin
            cmp_lt = 0;
            cmp_eq = 0;
            minmax_sel_a = (s1_b_is_nan ? 1 : 0);
        end else begin
            if ((s1_a_is_zero & s1_b_is_zero)) begin
                cmp_lt = 0;
                cmp_eq = 1;
                minmax_sel_a = 0;
            end else begin
                if ((s1_a_sign != s1_b_sign)) begin
                    cmp_eq = 0;
                    if ((s1_a_sign == 1)) begin
                        cmp_lt = 1;
                        minmax_sel_a = ((s1_op == 3) ? 1 : 0);
                    end else begin
                        cmp_lt = 0;
                        minmax_sel_a = ((s1_op == 3) ? 0 : 1);
                    end
                end else begin
                    cmp_eq = (s1_a_mag == s1_b_mag);
                    if ((s1_a_sign == 0)) begin
                        cmp_lt = (s1_a_mag < s1_b_mag);
                        minmax_sel_a = ((s1_op == 3) ? (s1_a_mag < s1_b_mag) : (s1_a_mag > s1_b_mag));
                    end else begin
                        cmp_lt = (s1_a_mag > s1_b_mag);
                        minmax_sel_a = ((s1_op == 3) ? (s1_a_mag > s1_b_mag) : (s1_a_mag < s1_b_mag));
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
            default: s2_is_nan_in = ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 0) | (s1_op == 1))) & (s1_a_sign != add_eff_b_sign)));
        endcase
        case (s1_op)
            2: s2_is_inf_in = (((s1_a_is_inf | s1_b_is_inf) | ((mul_exp >= 31) & (~mul_exp[6]))) & (~((s1_op == 2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 0) | (s1_op == 1))) & (s1_a_sign != add_eff_b_sign))))));
            default: s2_is_inf_in = (((s1_a_is_inf | s1_b_is_inf) | ((add_norm_exp >= 31) & (~add_norm_exp[6]))) & (~((s1_op == 2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 0) | (s1_op == 1))) & (s1_a_sign != add_eff_b_sign))))));
        endcase
        s2_is_zero_in = ((((s1_op == 2) ? (s1_a_is_zero | s1_b_is_zero) : ((add_res_mag == 0) & ((s1_op == 0) | (s1_op == 1)))) & (~((s1_op == 2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 0) | (s1_op == 1))) & (s1_a_sign != add_eff_b_sign)))))) & (~((s1_op == 2) ? (((s1_a_is_inf | s1_b_is_inf) | ((mul_exp >= 31) & (~mul_exp[6]))) & (~((s1_op == 2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 0) | (s1_op == 1))) & (s1_a_sign != add_eff_b_sign)))))) : (((s1_a_is_inf | s1_b_is_inf) | ((add_norm_exp >= 31) & (~add_norm_exp[6]))) & (~((s1_op == 2) ? (((s1_a_is_nan | s1_b_is_nan) | (s1_a_is_inf & s1_b_is_zero)) | (s1_a_is_zero & s1_b_is_inf)) : ((s1_a_is_nan | s1_b_is_nan) | (((s1_a_is_inf & s1_b_is_inf) & ((s1_op == 0) | (s1_op == 1))) & (s1_a_sign != add_eff_b_sign)))))))));
        s2_cmp_lt_in = cmp_lt;
        s2_cmp_eq_in = cmp_eq;
        s2_minmax_sel_a_in = minmax_sel_a;
    end

    always @(*) begin
        if (s2_is_nan) begin
            arith_result = {0, 31, 1};
        end else begin
            if ((s2_is_inf | ((s2_res_exp >= 31) & (~s2_res_exp[6])))) begin
                arith_result = {s2_res_sign, 31, 0};
            end else begin
                if ((s2_is_zero | s2_res_exp[6])) begin
                    arith_result = {s2_res_sign, 0, 0};
                end else begin
                    arith_result = {s2_res_sign, s2_res_exp[4:0], s2_res_mant[1:0]};
                end
            end
        end
        cmp_result = {0, ((s2_op == 5) ? s2_cmp_lt : s2_cmp_eq)};
        minmax_result = (s2_minmax_sel_a ? s2_minmax_a : s2_minmax_b);
        if (((s2_op == 5) | (s2_op == 6))) begin
            final_result = cmp_result;
        end else begin
            if (((s2_op == 3) | (s2_op == 4))) begin
                final_result = minmax_result;
            end else begin
                final_result = arith_result;
            end
        end
        final_flags = {(s2_is_nan & (((s2_op == 0) | (s2_op == 1)) | (s2_op == 2))), (s2_is_inf & (((s2_op == 0) | (s2_op == 1)) | (s2_op == 2))), (((s2_is_zero & (~(s2_is_nan & (((s2_op == 0) | (s2_op == 1)) | (s2_op == 2))))) & (~(s2_is_inf & (((s2_op == 0) | (s2_op == 1)) | (s2_op == 2))))) & (((s2_op == 0) | (s2_op == 1)) | (s2_op == 2))), 0};
    end

    assign o_valid = o_valid_reg;
    assign result = result_reg;
    assign flags = flags_reg;

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            s1_valid <= 0;
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
                end
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
        end else begin
            if ((s1_ready & i_valid)) begin
                s1_a_raw <= a;
                s1_b_raw <= b;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if ((rst_n == 0)) begin
            s2_valid <= 0;
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
        if ((rst_n == 0)) begin
            o_valid_reg <= 0;
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
