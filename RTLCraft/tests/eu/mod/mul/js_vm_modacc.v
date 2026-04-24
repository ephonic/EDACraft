//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2024/06/14 12:33:36
// Design Name: 
// Module Name: mdc_ntt_modadd_level1
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module js_vm_modacc
(
    clk,
    rstn,
    data,
    q,
    res,
    i_vm_id,
    o_vm_id,
    i_valid,
    o_valid,
    i_ready,
    o_ready
);

`include "js_vm.vh"
localparam  EXT_BITS = 8;
localparam  PART     = 4;
localparam  SEG_WIDTH= (DATA_WIDTH+EXT_BITS+PART-1)/PART; //ceil
input wire clk;
input wire rstn;
input wire [ISA_BITS+REG_WIDTH+1-1:0] data;
input wire [DATA_WIDTH-1:0] q;
input wire [3:0]           i_vm_id;
input wire                 i_valid;
input wire                 o_ready;
output wire [3:0]          o_vm_id;
output wire                o_valid;
output wire                i_ready;
output wire [ISA_BITS+REG_WIDTH+1-1:0] res;

wire [ISA_BITS-1 :0] isa;
wire                 cc_val;
wire [REG_WIDTH-DATA_WIDTH-1:0] flag_bits;
reg  [ISA_BITS-1 :0]            s0_isa;
reg                             s0_cc_val;
reg  [3:0]                      s0_vm_id;
reg                             s0_b_is_one;
reg  [ISA_BITS-1 :0]            s1_isa[EXT_BITS-1:0];
reg                             s1_cc_val[EXT_BITS-1:0];
reg  [3:0]                      s1_vm_id[EXT_BITS-1:0];
reg                             s1_b_is_one[EXT_BITS-1:0];
wire [REG_WIDTH-1:0] a;
wire [PART*SEG_WIDTH-1:0] a_ext;
wire [PART*SEG_WIDTH-1:0] b_ext;
wire [PART*SEG_WIDTH-1:0] q_redc_ext [EXT_BITS-1:0];
reg  [DATA_WIDTH-1:0] q_r;
reg  [DATA_WIDTH-1:0] q_redc [EXT_BITS-1:0];
wire [SEG_WIDTH-1:0]  a_seg  [PART-1:0];
wire [SEG_WIDTH-1:0]  b_seg  [PART-1:0];
wire [SEG_WIDTH-1:0]  q_seg  [EXT_BITS-1:0][PART-1:0];
wire [SEG_WIDTH-1:0]  s0_sum_0;
wire [SEG_WIDTH-1:0]  s0_sum_seg_0 [PART-2:0];
wire [SEG_WIDTH-1:0]  s0_sum_seg_1 [PART-2:0];
wire [PART-1:0]       s0_carry_seg;
wire [PART-2:0]       s0_carry_seg_0;
wire [PART-2:0]       s0_carry_seg_1;
reg  [SEG_WIDTH-1:0]  s0_sum_seg_r[PART-1:0];
reg                   s0_carry_r;
wire [SEG_WIDTH-1:0]  s0_sum_seg  [PART-1:0];
wire                  s0_carry;
wire [SEG_WIDTH-1:0]  to_redc_seg  [PART-1:0];
wire [SEG_WIDTH-1:0]  s1_sum_1     [EXT_BITS-1:0];
wire [SEG_WIDTH-1:0]  s1_sum_seg_0 [EXT_BITS-1:0][PART-2:0];
wire [SEG_WIDTH-1:0]  s1_sum_seg_1 [EXT_BITS-1:0][PART-2:0];
wire [PART-1:0]       s1_carry_seg [EXT_BITS-1:0];
wire [PART-2:0]       s1_carry_seg_0[EXT_BITS-1:0];
wire [PART-2:0]       s1_carry_seg_1[EXT_BITS-1:0];
reg  [SEG_WIDTH-1:0]  s1_sum_seg_r  [EXT_BITS-1:0][PART-1:0];
wire [PART*SEG_WIDTH-1:0] res_tmp;
reg  [PART*SEG_WIDTH-1:0] acc_reg    [15:0];
reg  [PART*SEG_WIDTH-1:0] acc_reg_d1 [15:0];
wire [PART*SEG_WIDTH-1:0] acc_res;
reg  [EXT_BITS-1:0]       acc_count  [15:0];
wire                      acc_overflow;
reg  [EXT_BITS-1:0]       acc_update;
wire [REG_WIDTH-1:0]      add_a;
wire [PART*SEG_WIDTH-1:0] add_b;
wire [ISA_DST_FMT_BITS-1:0]        i_dst_fmt;
reg  [ISA_DST_FMT_BITS-1:0]        s0_dst_fmt;
wire [ISA_DST_FMT_BITS-1:0]        o_dst_fmt;
wire                 pipe_en0;
wire                 pipe_en1[EXT_BITS-1:0];
wire                 pipe_i_valid0;
wire                 pipe_i_ready0;
reg                  pipe_o_valid0;
wire                 pipe_o_ready0;
wire                 pipe_i_valid1[EXT_BITS-1:0];
wire                 pipe_i_ready1[EXT_BITS-1:0];
reg                  pipe_o_valid1[EXT_BITS-1:0];
wire                 pipe_o_ready1[EXT_BITS-1:0];

assign {isa, cc_val, a} = data;
assign i_dst_fmt           = isa[82:79];
assign add_a               = a;
assign add_b               = acc_reg[i_vm_id];
assign a_ext               = {{(PART*SEG_WIDTH-DATA_WIDTH){1'b0}} ,add_a[DATA_WIDTH-1:0]};
assign b_ext               = add_b;
/////pipeline Stage 0///
genvar part,redc;
generate
    for (part=0; part<PART; part=part+1) begin: stage0
        assign a_seg[part][SEG_WIDTH-1:0] = a_ext[(part+1)*SEG_WIDTH-1:part*SEG_WIDTH]; 
        assign b_seg[part][SEG_WIDTH-1:0] = b_ext[(part+1)*SEG_WIDTH-1:part*SEG_WIDTH];
        if (part==0) begin
            assign {s0_carry_seg[part], s0_sum_0} = a_seg[part] + b_seg[part];
            assign s0_sum_seg[part]               = s0_sum_0;
        end
        else begin
            assign {s0_carry_seg_0[part-1], s0_sum_seg_0[part-1]} = a_seg[part] + b_seg[part];
            assign {s0_carry_seg_1[part-1], s0_sum_seg_1[part-1]} = a_seg[part] + b_seg[part] + 1'b1;
            assign s0_carry_seg[part]                             = s0_carry_seg[part-1] ? s0_carry_seg_1[part-1] : s0_carry_seg_0[part-1];
            assign s0_sum_seg[part]                               = s0_carry_seg[part-1] ? s0_sum_seg_1[part-1] : s0_sum_seg_0[part-1];
        end
        always @ (posedge clk) begin
            if (pipe_en0) begin
                s0_sum_seg_r[part] <= s0_sum_seg[part];
            end
            else begin
                s0_sum_seg_r[part] <= s0_sum_seg_r[part];
            end
        end 
        assign acc_res[(part+1)*SEG_WIDTH-1:part*SEG_WIDTH] = s0_sum_seg[part];
    end
endgenerate
//acc register update
genvar i;
generate 
    for(i=0; i<16; i=i+1) begin
always @ (posedge clk or negedge rstn) begin
    if (!rstn) begin
            acc_reg[i]    <= 'h0;
            acc_count[i]  <= 'h0;
    end
    else if (pipe_en0) begin
        if (i_dst_fmt == 4'hb && i==i_vm_id) begin
            acc_reg[i]   <= acc_res;
            acc_count[i] <= acc_count[i] + 1;
        end
        else if (i_dst_fmt == 4'hc && i==i_vm_id) begin
            acc_reg[i]   <= 'h0;
            acc_count[i] <= 'h0;
        end
    end
    else if (acc_update[EXT_BITS-1]&&acc_overflow && i==s1_vm_id[EXT_BITS-1]) begin
        acc_reg[i] <= {{(PART*SEG_WIDTH-DATA_WIDTH){1'b0}} ,res_tmp[DATA_WIDTH-1:0]};
        acc_count[i] <= 'h0;
    end
end
    end
endgenerate

/*
always @ (posedge clk or negedge rstn) begin
    if (!rstn) begin
        for (integer i=0; i<16; i=i+1) begin
            acc_reg[i]    <= 'h0;
            acc_count[i]  <= 'h0;
        end
    end
    else if (pipe_en0) begin
        if (i_dst_fmt == 4'hb) begin
            acc_reg[i_vm_id]   <= acc_res;
            acc_count[i_vm_id] <= acc_count[i_vm_id] + 1;
        end
        else if (i_dst_fmt == 4'hc) begin
            acc_reg[i_vm_id]   <= 'h0;
            acc_count[i_vm_id] <= 'h0;
        end
    end
    else if (acc_update[EXT_BITS-1]&&acc_overflow) begin
        acc_reg[s1_vm_id[EXT_BITS-1]] <= {{(PART*SEG_WIDTH-DATA_WIDTH){1'b0}} ,res_tmp[DATA_WIDTH-1:0]};
        acc_count[s1_vm_id[EXT_BITS-1]] <= 'h0;
    end
end
*/
assign acc_overflow = acc_count[s0_vm_id]==2**EXT_BITS-1;

always @ (posedge clk or negedge rstn) begin
    if (!rstn) begin
        q_r          <= 'h0; 
        s0_isa       <= 'h0; 
        s0_cc_val    <= 'h0; 
        s0_vm_id     <= 'h0; 
        s0_dst_fmt   <= 'h0; 
    end
    else if (pipe_en0) begin
        q_r          <= ~q;
        s0_isa       <= isa;
        s0_cc_val    <= cc_val;
        s0_vm_id     <= i_vm_id;
        s0_dst_fmt   <= i_dst_fmt;
    end
    else begin
        q_r          <= q_r;
        s0_isa       <= s0_isa;
        s0_cc_val    <= s0_cc_val;
        s0_vm_id     <= s0_vm_id;
        s0_dst_fmt   <= s0_dst_fmt;
    end
end
///pipeline stage 1////
generate
for (redc=0; redc<EXT_BITS; redc=redc+1) begin: REDUCTION
    if (redc==0) begin
        assign q_redc_ext[redc] = {{(PART*SEG_WIDTH-DATA_WIDTH-EXT_BITS+1+redc){1'b1}}, q_r, {(EXT_BITS-1-redc){1'b1}}};
        for (part=0; part<PART; part=part+1) begin: STAGE
            assign to_redc_seg[part]                = s0_sum_seg_r[part];
            assign q_seg[redc][part][SEG_WIDTH-1:0] = q_redc_ext[redc][(part+1)*SEG_WIDTH-1:part*SEG_WIDTH]; 
            if (part == 0) begin
                assign {s1_carry_seg[redc][part], s1_sum_1[redc]} = to_redc_seg[part] + q_seg[redc][part] + 1'b1;
                always @ (posedge clk) begin
                    if (pipe_en1[redc]) begin
                        s1_sum_seg_r[redc][part] <= (s1_carry_seg[redc][PART-1]) ? s1_sum_1[redc] : to_redc_seg[part]; //////1
                    end
                    else begin
                        s1_sum_seg_r[redc][part] <= s1_sum_seg_r[redc][part]; 
                    end
                end
            end
            else begin
                assign {s1_carry_seg_0[redc][part-1], s1_sum_seg_0[redc][part-1]} = to_redc_seg[part] + q_seg[redc][part];
                assign {s1_carry_seg_1[redc][part-1], s1_sum_seg_1[redc][part-1]} = to_redc_seg[part] + q_seg[redc][part] + 1'b1;
                assign s1_carry_seg[redc][part]                                   = s1_carry_seg[redc][part-1] ? s1_carry_seg_1[redc][part-1] : s1_carry_seg_0[redc][part-1];
                always @ (posedge clk) begin
                    if (pipe_en1[redc]) begin
                        s1_sum_seg_r[redc][part] <= (s1_carry_seg[redc][PART-1]) ? (s1_carry_seg[redc][part-1] ? s1_sum_seg_1[redc][part-1] : s1_sum_seg_0[redc][part-1]) : to_redc_seg[part];
                    end
                    else begin
                        s1_sum_seg_r[redc][part] <= s1_sum_seg_r[redc][part];
                    end
                end            
            end
        end
        always @ (posedge clk or negedge rstn) begin
            if (!rstn) begin
                s1_isa     [redc]  <= 'h0;
                s1_cc_val  [redc]  <= 'h0;
                s1_vm_id   [redc]  <= 'h0;
                s1_b_is_one[redc]  <= 'h0;
                q_redc     [redc]  <= 'h0;
                acc_update [redc]  <= 'h0;
            end
            else if (pipe_en1[redc]) begin
                s1_isa     [redc]  <= s0_isa;
                s1_cc_val  [redc]  <= s0_cc_val;
                s1_vm_id   [redc]  <= s0_vm_id;
                q_redc     [redc]  <= q_r;
                acc_update [redc]  <= acc_overflow;
            end
            else begin
                s1_isa     [redc]  <= s1_isa     [redc];
                s1_cc_val  [redc]  <= s1_cc_val  [redc];
                s1_vm_id   [redc]  <= s1_vm_id   [redc];
                q_redc     [redc]  <= q_redc     [redc];
                acc_update [redc]  <= acc_update [redc];
            end
        end
    end
    else begin
        assign q_redc_ext[redc] = {{(PART*SEG_WIDTH-DATA_WIDTH-EXT_BITS+1+redc){1'b1}}, q_redc[redc-1], {(EXT_BITS-1-redc){1'b1}}};
        for (part=0; part<PART; part=part+1) begin: STAGE
            assign q_seg[redc][part][SEG_WIDTH-1:0] = q_redc_ext[redc][(part+1)*SEG_WIDTH-1:part*SEG_WIDTH]; 
            if (part == 0) begin
                assign {s1_carry_seg[redc][part], s1_sum_1[redc]} = s1_sum_seg_r[redc-1][part] + q_seg[redc][part] + 1'b1;
                always @ (posedge clk) begin
                    if (pipe_en1[redc]) begin
                        s1_sum_seg_r[redc][part] <= (s1_carry_seg[redc][PART-1]) ? s1_sum_1[redc] : s1_sum_seg_r[redc-1][part]; //////1
                    end
                    else begin
                        s1_sum_seg_r[redc][part] <= s1_sum_seg_r[redc][part]; 
                    end
                end
            end
            else begin
                assign {s1_carry_seg_0[redc][part-1], s1_sum_seg_0[redc][part-1]} = s1_sum_seg_r[redc-1][part] + q_seg[redc][part];
                assign {s1_carry_seg_1[redc][part-1], s1_sum_seg_1[redc][part-1]} = s1_sum_seg_r[redc-1][part] + q_seg[redc][part] + 1'b1;
                assign s1_carry_seg[redc][part]                                   = s1_carry_seg[redc][part-1] ? s1_carry_seg_1[redc][part-1] : s1_carry_seg_0[redc][part-1];
                always @ (posedge clk) begin
                    if (pipe_en1[redc]) begin
                        s1_sum_seg_r[redc][part] <= (s1_carry_seg[redc][PART-1]) ? (s1_carry_seg[redc][part-1] ? s1_sum_seg_1[redc][part-1] : s1_sum_seg_0[redc][part-1]) : s1_sum_seg_r[redc-1][part];
                    end
                    else begin
                        s1_sum_seg_r[redc][part] <= s1_sum_seg_r[redc][part];
                    end
                end            
            end
            if (redc==EXT_BITS-1) begin
                assign res_tmp[(part+1)*SEG_WIDTH-1:part*SEG_WIDTH] = s1_sum_seg_r[EXT_BITS-1][part];
            end
        end
        always @ (posedge clk or negedge rstn) begin
            if (!rstn) begin
                s1_isa     [redc]  <= 'h0;
                s1_cc_val  [redc]  <= 'h0;
                s1_vm_id   [redc]  <= 'h0;
                s1_b_is_one[redc]  <= 'h0;
                q_redc     [redc]  <= 'h0;
                acc_update [redc]  <= 'h0;
            end
            else if (pipe_en1[redc]) begin
                s1_isa     [redc]  <= s1_isa     [redc-1];
                s1_cc_val  [redc]  <= s1_cc_val  [redc-1];
                s1_vm_id   [redc]  <= s1_vm_id   [redc-1];
                q_redc     [redc]  <= q_redc     [redc-1];
                acc_update [redc]  <= acc_update [redc-1];
            end
            else begin
                s1_isa     [redc]  <= s1_isa     [redc];
                s1_cc_val  [redc]  <= s1_cc_val  [redc];
                s1_vm_id   [redc]  <= s1_vm_id   [redc];
                q_redc     [redc]  <= q_redc     [redc];
                acc_update [redc]  <= acc_update [redc];
            end
        end

    end
    if (redc == 0) begin
        assign pipe_i_valid1[redc] = pipe_o_valid0;
        assign pipe_o_ready1[redc] = pipe_i_ready1[redc+1];
    end
    else if (redc == EXT_BITS -1 ) begin
        assign pipe_i_valid1[redc] = pipe_o_valid1[redc-1];
        assign pipe_o_ready1[redc] = o_ready;
    end
    else begin
        assign pipe_i_valid1[redc] = pipe_o_valid1[redc-1];
        assign pipe_o_ready1[redc] = pipe_i_ready1[redc+1];
    end
    assign pipe_en1[redc] = pipe_i_valid1[redc] &  pipe_i_ready1[redc];
    assign pipe_i_ready1[redc] = !pipe_o_valid1[redc] | pipe_o_ready1[redc];
    always @ (posedge clk or negedge rstn) begin
        if (!rstn)
            pipe_o_valid1[redc] <= 0;
        else if (pipe_i_ready1[redc])
            pipe_o_valid1[redc] <= pipe_i_valid1[redc];
        else
            pipe_o_valid1[redc] <= pipe_o_valid1[redc];
    end
            
end
endgenerate


//output
assign o_dst_fmt = s1_isa[EXT_BITS-1][82:79];
assign res       = {s1_isa[EXT_BITS-1], s1_cc_val[EXT_BITS-1], {(REG_WIDTH-DATA_WIDTH){1'b0}}, res_tmp[DATA_WIDTH-1:0]};
assign o_vm_id   = s1_vm_id[EXT_BITS-1];
//handshake
assign pipe_en0      = pipe_i_valid0 & pipe_i_ready0;
assign pipe_i_valid0 = i_valid;
assign pipe_o_ready0 = pipe_i_ready1[0];
assign pipe_i_ready0 = !pipe_o_valid0 | pipe_o_ready0;
assign i_ready       = pipe_i_ready0 && !acc_overflow;
assign o_valid       = pipe_o_valid1[EXT_BITS-1];
always @ (posedge clk or negedge rstn) begin
    if (!rstn) begin
        pipe_o_valid0 <= 0;
    end
    else if (pipe_i_ready0) begin
        pipe_o_valid0 <= pipe_i_valid0;
    end
    else begin
        pipe_o_valid0 <= pipe_o_valid0;
    end
end



endmodule
