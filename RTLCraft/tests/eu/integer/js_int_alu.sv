module js_int_alu (/*AUTOARG*/
   // Outputs
   ready_i, valid_o, data_o, vm_id_o,
   // Inputs
   clk, rstn, valid_i, vm_id_i, data_i, ready_o
   );
`include "js_vm.vh"

    input wire      clk;                      // Clock signal
    input wire      rstn;                    // Active low reset signal
    input wire      valid_i;                  // Input valid signal
    input  [3:0]    vm_id_i;
    input           [ISA_BITS+2*REG_WIDTH+1-1:0] data_i;
    output          ready_i;                  // Ready to accept new inputs
    output          valid_o;                  // Indicates addition completion
    input           ready_o;                   // Ready to accept output
    output          [ISA_BITS+REG_WIDTH+1-1:0] data_o;
    output [3:0]    vm_id_o;


reg valid_p1, valid_p2, valid_p3;
wire    ready_p1, ready_p2, ready_p3;
wire    en0, en1, en2, en3;
always @(posedge clk or negedge rstn)
if(!rstn) begin
    valid_p1    <= 1'b0;
    valid_p2    <= 1'b0;
    valid_p3    <= 1'b0;
end else begin
    if(ready_i)
        valid_p1 <= valid_i;
    if(ready_p1)
        valid_p2 <= valid_p1;
    if(ready_p2)
        valid_p3 <= valid_p2;
end
assign ready_i = ready_p1 || !valid_p1;
assign ready_p1 = ready_p2 || !valid_p2;
assign ready_p2 = ready_p3 || !valid_p3;
assign ready_p3 = ready_o;
assign valid_o  = valid_p3;
assign en0 = valid_i && ready_i;
assign en1 = valid_p1 && ready_p1;
assign en2 = valid_p2 && ready_p2;
assign en3 = valid_p3 && ready_p3;


//generate oprand_a and operand_b
logic signed_mode;              // 1: Signed addition, 0: Unsigned addition
logic [127:0] operand_a;        // 128-bit operand A
logic [127:0] operand_b;        // 128-bit operand B
logic [127:0] sum;              // 128-bit sum result
wire    [ISA_OPTYPE_BITS-1:0]       optype;
wire    [ISA_OPCODE_BITS-1:0]       opcode;
wire    [ISA_CC_BITS-1:0]           cc_reg;
wire    [ISA_SF_BITS-1:0]           sf;
wire    [ISA_WF_BITS-1:0]           wf;
wire    [ISA_SRC0_REG_BITS-1:0]     src0_reg;
wire    [ISA_SRC0_TYPE_BITS-1:0]    src0_type;
wire    [ISA_SRC0_FMT_BITS-1:0]     src0_fmt;
wire    [ISA_SRC0_IMM_BITS-1:0]     src0_imm;
wire    [ISA_SRC1_REG_BITS-1:0]     src1_reg;
wire    [ISA_SRC1_TYPE_BITS-1:0]    src1_type;
wire    [ISA_SRC1_FMT_BITS-1:0]     src1_fmt;
wire    [ISA_SRC1_IMM_BITS-1:0]     src1_imm;
wire    [ISA_DST0_REG_BITS-1:0]     dst0_reg;
wire    [ISA_DST1_REG_BITS-1:0]     dst1_reg;
wire    [ISA_DST_TYPE_BITS-1:0]     dst_type;
wire    [ISA_DST_FMT_BITS-1:0]      dst_fmt;
wire    [ISA_RSV_BITS-1:0]          rsv;
logic[REG_WIDTH-1:0] src0_data;
logic[REG_WIDTH-1:0] src1_data;
logic[ISA_BITS-1 :0] alu_isa;
logic alu_cc_value;
logic [ISA_SRC0_FMT_BITS-2:0] flag_bits;

assign {alu_isa,alu_cc_value,src1_data,src0_data} = data_i;
assign {rsv,
        dst_fmt,
        dst_type,
        dst1_reg,
        dst0_reg,
        src1_imm,
        src1_fmt,
        src1_type,
        src1_reg,
        src0_imm,
        src0_fmt,
        src0_type,
        src0_reg,
        wf,
        sf,
        cc_reg,
        opcode,
        optype
        } = alu_isa;
assign flag_bits   = src0_fmt[ISA_SRC0_FMT_BITS-1:1];
assign signed_mode = src0_fmt[0];

wire operand_a_sign =  (flag_bits==3'h0 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h0 && signed_mode == 1'b0) ? src0_data[7] :
                    (flag_bits==3'h1 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h1 && signed_mode == 1'b0) ? src0_data[15] :
                    (flag_bits==3'h2 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h2 && signed_mode == 1'b0) ? src0_data[31] :
                    (flag_bits==3'h3 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h3 && signed_mode == 1'b0) ? src0_data[63] :
                    (flag_bits==3'h4 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h4 && signed_mode == 1'b0) ? src0_data[127] : 1'b0;

wire operand_b_sign =  (flag_bits==3'h0 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h0 && signed_mode == 1'b0) ? src1_data[7] :
                    (flag_bits==3'h1 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h1 && signed_mode == 1'b0) ? src1_data[15] :
                    (flag_bits==3'h2 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h2 && signed_mode == 1'b0) ? src1_data[31] :
                    (flag_bits==3'h3 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h3 && signed_mode == 1'b0) ? src1_data[63] :
                    (flag_bits==3'h4 && signed_mode == 1'b1) ? 1'b0 :
                    (flag_bits==3'h4 && signed_mode == 1'b0) ? src1_data[127] : 1'b0;

assign operand_a =  (flag_bits==3'h0 && signed_mode == 1'b1) ? {{120{1'b0}},src0_data[7:0]} :
                    (flag_bits==3'h0 && signed_mode == 1'b0) ? {{120{src0_data[7]}},src0_data[7:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b1) ? {{112{1'b0}},src0_data[15:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b0) ? {{112{src0_data[15]}},src0_data[15:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b1) ? {{96{1'b0}},src0_data[31:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b0) ? {{96{src0_data[31]}},src0_data[31:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b1) ? {{64{1'b0}},src0_data[63:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b0) ? {{64{src0_data[63]}},src0_data[63:0]} :
                    (flag_bits==3'h4 && signed_mode == 1'b1) ? src0_data[127:0] :
                    (flag_bits==3'h4 && signed_mode == 1'b0) ? src0_data[127:0] : 'd0;
                                                         
assign operand_b =  (flag_bits==3'h0 && signed_mode == 1'b1) ? {{120{1'b0}},src1_data[7:0]} :
                    (flag_bits==3'h0 && signed_mode == 1'b0) ? {{120{src1_data[7]}},src1_data[7:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b1) ? {{112{1'b0}},src1_data[15:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b0) ? {{112{src1_data[15]}},src1_data[15:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b1) ? {{96{1'b0}},src1_data[31:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b0) ? {{96{src1_data[31]}},src1_data[31:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b1) ? {{64{1'b0}},src1_data[63:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b0) ? {{64{src1_data[63]}},src1_data[63:0]} :
                    (flag_bits==3'h4 && signed_mode == 1'b1) ? src1_data[127:0] :
                    (flag_bits==3'h4 && signed_mode == 1'b0) ? src1_data[127:0] : 'd0;

wire    [127:0] a_abs = operand_a_sign ? ~operand_a + 1 : operand_a;
wire    [127:0] b_abs = operand_b_sign ? ~operand_b + 1 : operand_b;
wire    [127:0] b_neg = ~operand_b + 1;

wire    is_mult = opcode == 3'd2;
wire    is_add  = opcode == 3'd0;
wire    is_sub  = opcode == 3'd1;

reg [127:0]     op_a_p1, op_b_p1;
reg op_a_sign_p1, op_b_sign_p1;
reg [ISA_BITS-1:0]  alu_isa_p1;
reg [2:0]   opcode_p1;
reg [2:0]   flag_p1;
reg [3:0]   vm_id_p1;
always @(posedge clk)
if(en0) begin
    op_a_sign_p1 <= operand_a_sign;
    op_b_sign_p1 <= operand_b_sign;
    op_a_p1      <= is_mult ? a_abs : operand_a;
    op_b_p1      <= is_mult ? b_abs : is_sub ? b_neg : operand_b;
    alu_isa_p1  <= alu_isa;
    opcode_p1   <= opcode;
    flag_p1     <= flag_bits;
    vm_id_p1    <= vm_id_i;
end
wire    is_add_p1 = opcode_p1 == 3'd0;
wire    is_sub_p1 = opcode_p1 == 3'd1;
wire    is_mul_p1 = opcode_p1 == 3'd2;
wire    [127:0] ab_add_res = op_a_p1 + op_b_p1;
wire    [127:0] ab_mul_00  = op_a_p1[63:0] * op_b_p1[63:0];
wire    [127:0] ab_mul_01  = op_a_p1[63:0] * op_b_p1[127:64];
wire    [127:0] ab_mul_10  = op_a_p1[127:64] * op_b_p1[63:0];
wire    [127:0] ab_mul_11  = op_a_p1[127:64] * op_b_p1[127:64];
wire    ab_mul_sign = op_a_sign_p1 ^ op_b_sign_p1;

reg     ab_mul_sign_p2;
reg [127:0] ab_tmp_00_p2, ab_tmp_01_p2, ab_tmp_10_p2, ab_tmp_11_p2;
reg [ISA_BITS-1:0]  alu_isa_p2;
reg [2:0]   opcode_p2;
reg [2:0]   flag_p2;
reg [3:0]   vm_id_p2;
always @(posedge clk)
if(en1) begin
    ab_mul_sign_p2 <= ab_mul_sign;
    ab_tmp_00_p2   <= is_mul_p1 ? ab_mul_00 : ab_add_res;
    ab_tmp_01_p2   <= ab_mul_01;
    ab_tmp_10_p2   <= ab_mul_10;
    ab_tmp_11_p2   <= ab_mul_11;
    alu_isa_p2     <= alu_isa_p1;
    opcode_p2      <= opcode_p1;
    flag_p2         <= flag_p1;
    vm_id_p2        <= vm_id_p1;
end
wire    is_mul_p2 = opcode_p2 == 3'd2;
wire    [255:0] ab_mul_tmp = ab_tmp_00_p2 + {ab_tmp_01_p2, 64'b0} + {ab_tmp_10_p2, 64'b0} + {ab_tmp_11_p2, 128'b0};
wire    [255:0] ab_op_res = is_mul_p2 ? (ab_mul_sign_p2 ? ~ab_mul_tmp + 1 : ab_mul_tmp) : {128'b0, ab_tmp_00_p2};

reg [255:0] ab_res_p3;
reg [ISA_BITS-1:0]   alu_isa_p3;
reg [2:0]   flag_p3;
reg [3:0]   vm_id_p3;
always @(posedge clk)
if(en2) begin
    ab_res_p3 <= ab_op_res;
    alu_isa_p3 <= alu_isa_p2;
    flag_p3         <= flag_p2;
    vm_id_p3        <= vm_id_p2;
end
wire    [127:0] alu_res;
assign alu_res =    flag_p3==3'd0 ? {120'b0, ab_res_p3[7:0]} :
                    flag_p3==3'd1 ? {112'b0, ab_res_p3[15:0]} :
                    flag_p3==3'd2 ? {96'b0,  ab_res_p3[31:0]} :
                    flag_p3==3'd3 ? {64'b0,  ab_res_p3[63:0]} : 
                    flag_p3==3'd4 ? ab_res_p3[127:0] : 128'b0;

assign data_o = {alu_isa_p3, 1'b0, {(REG_WIDTH-128){1'b0}}, alu_res};
assign vm_id_o = vm_id_p3;

endmodule
