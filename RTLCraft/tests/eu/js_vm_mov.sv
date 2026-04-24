module js_vm_mov (/*AUTOARG*/
   // Outputs
   sq_mov_ready, mov_sq_fc_dec, mov_sq_fc_dec_vm_id, mov_res_valid,
   mov_res_vm_id, mov_res_data,
   // Inputs
   clk, rstn, sq_mov_valid, sq_mov_data, sq_mov_vm_id, mov_res_ready
   );
`include "js_vm.vh"

input           clk;
input           rstn;


input           sq_mov_valid;   // move
input   [ISA_BITS+2*REG_WIDTH+1-1:0] sq_mov_data;
input   [3:0]   sq_mov_vm_id;
output          sq_mov_ready;

output  [FC_NUM-1:0]   mov_sq_fc_dec;
output  [3:0]   mov_sq_fc_dec_vm_id;


output          mov_res_valid;
output  [3:0]   mov_res_vm_id;
output  [ISA_BITS+REG_WIDTH+1-1:0]  mov_res_data;
input           mov_res_ready;


//-----------------------------------------------
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
wire    [ISA_SF_EXT_BITS-1:0]       sf_ext;
wire    [ISA_WF_EXT_BITS-1:0]       wf_ext;
wire    [ISA_RSV_EXT_BITS-1:0]      rsv;
wire                                cc_value;
wire    [REG_WIDTH-1:0]             src1_value;
wire    [REG_WIDTH-1:0]             src0_value;

reg     [DATA_WIDTH-1:0]            truncate_window;


assign {rsv,
        wf_ext,
        sf_ext,
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
        optype,
        cc_value,
        src1_value,
        src0_value
        } = sq_mov_data[ISA_BITS+2*REG_WIDTH+1-1:0];

wire    src0_tmp [REG_WIDTH-1:0];
wire    mov_zero = rsv==1'b1 && (src1_fmt==4'd10 ? src1_value[src1_imm]=='b0 : src1_value=='b0);
wire    [REG_WIDTH-1:0] src0_value_adj = mov_zero ? 'b0 : src0_value;
genvar i;
generate
    for (i=0; i<REG_WIDTH; i=i+1) begin: ASSIGN_SRC0
        if ((i>=0) & (i<DATA_WIDTH))
            assign src0_tmp[i] = src0_value_adj[i];
        else
            assign src0_tmp[i] = 1'b0;
    end
endgenerate
generate
    for (i=0; i<DATA_WIDTH; i=i+1) begin
        always @(*) begin
            truncate_window[i] = (i<src0_imm) ? 1'b1 : 1'b0;
        end
    end
endgenerate
wire    extracted_bit = src0_tmp[src0_imm];
wire    [           REG_WIDTH-1:0]  res_data_tmp   = opcode==OPCODE_MVR2C || (opcode==OPCODE_MVR2R && src0_fmt==4'd10)? {{(REG_WIDTH-1){1'b0}},extracted_bit}: 
                                                     opcode==OPCODE_MVCLRC ? {DATA_WIDTH{1'b0}} : 
                                                     opcode==OPCODE_MVBITS2MH ? {{(REG_WIDTH-DATA_WIDTH){1'b0}}, src0_value_adj[DATA_WIDTH-1:0] & truncate_window} : src0_value_adj;
wire    [ISA_BITS+1+REG_WIDTH-1:0]  res_data_d0    = {sq_mov_data[ISA_BITS+2*REG_WIDTH+1-1-:ISA_BITS], res_data_tmp[0], res_data_tmp};          

reg     res_valid;
reg     [ISA_BITS+1+REG_WIDTH-1:0]  res_data;
reg     [3:0]   res_vm_id;
reg     [GPR_ADDR_BITS-1:0]         res_gpr_addr;
reg     [1:0]   res_type;

always @(posedge clk or negedge rstn)
if(!rstn)
    res_valid   <= 1'b0;
else if(sq_mov_ready)
    res_valid   <= sq_mov_valid;

always @(posedge clk)
if(sq_mov_valid && sq_mov_ready) begin
    res_data    <= res_data_d0;
    res_vm_id   <= sq_mov_vm_id;
    res_gpr_addr    <= dst0_reg;
    res_type    <= dst_type;
end

assign sq_mov_ready = !res_valid || mov_res_ready;

assign mov_res_valid = res_valid;
assign mov_res_data  = res_data;
assign mov_res_vm_id = res_vm_id;




//--------------------------------------
wire    [FC_NUM-1:0]   fc_dec =  {sf_ext, sf};

reg [FC_NUM-1:0]   res_fc_dec;
always @(posedge clk or negedge rstn)
if(!rstn)
    res_fc_dec <= 'b0;
else if(sq_mov_valid && sq_mov_ready)
    res_fc_dec  <= fc_dec;


reg [FC_NUM-1:0]   mov_sq_fc_dec;
reg [3:0]   mov_sq_fc_dec_vm_id;
/*
always @(posedge clk or negedge rstn)
if(!rstn) begin
    mov_sq_fc_dec   <= 2'b00;
    mov_sq_fc_dec_vm_id <= 4'b0;
end else begin
    mov_sq_fc_dec   <= {2{mov_res_valid&&mov_res_ready}} & res_fc_dec;
    mov_sq_fc_dec_vm_id <= res_vm_id;
end
*/
always @* begin
    mov_sq_fc_dec   = {FC_NUM{mov_res_valid&&mov_res_ready}} & res_fc_dec;
    mov_sq_fc_dec_vm_id = res_vm_id;
end

function [FC_NUM-1:0] get_sf;
input   [ISA_BITS-1:0]  isa;

reg     [ISA_OPTYPE_BITS-1:0]       optype;
reg     [ISA_OPCODE_BITS-1:0]       opcode;
reg     [ISA_CC_BITS-1:0]           cc_reg;
reg     [ISA_SF_BITS-1:0]           sf;
reg     [ISA_WF_BITS-1:0]           wf;
reg     [ISA_SRC0_REG_BITS-1:0]     src0_reg;
reg     [ISA_SRC0_TYPE_BITS-1:0]    src0_type;
reg     [ISA_SRC0_FMT_BITS-1:0]     src0_fmt;
reg     [ISA_SRC0_IMM_BITS-1:0]     src0_imm;
reg     [ISA_SRC1_REG_BITS-1:0]     src1_reg;
reg     [ISA_SRC1_TYPE_BITS-1:0]    src1_type;
reg     [ISA_SRC1_FMT_BITS-1:0]     src1_fmt;
reg     [ISA_SRC1_IMM_BITS-1:0]     src1_imm;
reg     [ISA_DST0_REG_BITS-1:0]     dst0_reg;
reg     [ISA_DST1_REG_BITS-1:0]     dst1_reg;
reg     [ISA_DST_TYPE_BITS-1:0]     dst_type;
reg     [ISA_DST_FMT_BITS-1:0]      dst_fmt;
reg     [ISA_SF_EXT_BITS-1:0]       sf_ext;
reg     [ISA_WF_EXT_BITS-1:0]       wf_ext;
reg     [ISA_RSV_EXT_BITS-1:0]          rsv;

begin
   {rsv,
    wf_ext,
    sf_ext,
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
    optype} = isa[ISA_BITS-1:0];

    get_sf = {sf_ext, sf};
end
endfunction
endmodule
