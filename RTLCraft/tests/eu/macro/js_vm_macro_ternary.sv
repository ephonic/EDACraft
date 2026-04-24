
module js_vm_macro_ternary (
    clk,
    rstn,
    eu_macro_ternary_data,
    eu_macro_ternary_i_valid,
    eu_macro_ternary_i_vm_id,
    eu_macro_ternary_o_ready,
    eu_macro_ternary_o_valid,
    eu_macro_ternary_i_ready,
    eu_macro_ternary_o_vm_id,
    eu_macro_ternary_variable
);

`include "js_vm.vh"

input                                  clk;
input                                  rstn;
input    [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_ternary_data;
input                                  eu_macro_ternary_i_valid;
input    [3:0]                         eu_macro_ternary_i_vm_id;
input                                  eu_macro_ternary_o_ready;
output   logic                         eu_macro_ternary_o_valid;
output   logic                         eu_macro_ternary_i_ready;
output   logic [3:0]                   eu_macro_ternary_o_vm_id;
output   logic [ISA_BITS+REG_WIDTH:0]  eu_macro_ternary_variable;

reg [ISA_BITS:0] isa_r1;
reg [3:0]        vm_id;
reg              ternary_o_valid;
reg [REG_WIDTH-1:0] ternary_data;

wire[REG_WIDTH-1:0] operand_0; // y
wire[REG_WIDTH-1:0] operand_1; // x
reg [DATA_WIDTH-1:0]operand_ternary;
wire[DATA_WIDTH-1:0]operand_ternary_tmp;
wire[ISA_OPTYPE_BITS-1:0]       optype;
wire[ISA_OPCODE_BITS-1:0]       opcode;
wire[ISA_CC_BITS-1:0]           cc_reg;
wire[ISA_SF_BITS-1:0]           sf;
wire[ISA_WF_BITS-1:0]           wf;
wire[ISA_SRC0_REG_BITS-1:0]     src0_reg;
wire[ISA_SRC0_TYPE_BITS-1:0]    src0_type;
wire[ISA_SRC0_FMT_BITS-1:0]     src0_fmt;
wire[ISA_SRC0_IMM_BITS-1:0]     src0_imm;
wire[ISA_SRC1_REG_BITS-1:0]     src1_reg;
wire[ISA_SRC1_TYPE_BITS-1:0]    src1_type;
wire[ISA_SRC1_FMT_BITS-1:0]     src1_fmt;
wire[ISA_SRC1_IMM_BITS-1:0]     src1_imm;
wire[ISA_DST0_REG_BITS-1:0]     dst0_reg;
wire[ISA_DST1_REG_BITS-1:0]     dst1_reg;
wire[ISA_DST_TYPE_BITS-1:0]     dst_type;
wire[ISA_DST_FMT_BITS-1:0]      dst_fmt;
wire[ISA_RSV_BITS-1:0]          rsv;
wire[ISA_SRC0_IMM_BITS-1:0]     bit_nums;
assign eu_macro_ternary_i_ready = !eu_macro_ternary_o_valid|eu_macro_ternary_o_ready;
assign eu_macro_ternary_o_vm_id   = vm_id;
assign eu_macro_ternary_variable= {isa_r1,ternary_data};
assign eu_macro_ternary_o_valid = ternary_o_valid;

assign operand_1          = eu_macro_ternary_data[2*REG_WIDTH-1:REG_WIDTH];
assign operand_0          = eu_macro_ternary_data[REG_WIDTH-1:0];
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
        } = eu_macro_ternary_data[ISA_BITS+2*REG_WIDTH:2*REG_WIDTH+1]; 

assign operand_ternary_tmp    = eu_macro_ternary_data[2*REG_WIDTH] ? operand_0[DATA_WIDTH-1:0] : operand_1[DATA_WIDTH-1:0];
assign bit_nums              = src0_fmt=='d10 ? src0_imm :
                               src0_fmt=='d0 || src0_fmt=='d1 ? 'd8 :
                               src0_fmt=='d2 || src0_fmt=='d3 ? 'd16:
                               src0_fmt=='d4 || src0_fmt=='d5 ? 'd32:
                               src0_fmt=='d6 || src0_fmt=='d7 ? 'd64:
                               src0_fmt=='d8 || src0_fmt=='d9 ? 'd128 : 'd0;
genvar i;
generate
    for (i=0; i<DATA_WIDTH; i=i+1) begin
        always @(*) begin
            operand_ternary[i] = (i<bit_nums) ? operand_ternary_tmp[i]: 1'b0;
        end
    end
endgenerate

always @(posedge clk or negedge rstn) begin
    if(!rstn)begin
        isa_r1                            <= '0;
        vm_id                             <= '0;
    end
    else if(eu_macro_ternary_i_valid&&eu_macro_ternary_i_ready)begin
        isa_r1                            <= eu_macro_ternary_data[ISA_BITS+2*REG_WIDTH:2*REG_WIDTH];
        vm_id                             <= eu_macro_ternary_i_vm_id;        
    end
end

always @(posedge clk or negedge rstn) begin
    if(!rstn)begin
        ternary_o_valid                       <= '0;
    end
    else if(eu_macro_ternary_i_ready)begin
        ternary_o_valid                       <= eu_macro_ternary_i_valid;
    end
end

always @(posedge clk or negedge rstn) begin
    if(!rstn)begin
        ternary_data                          <= '0;
    end
    else if(eu_macro_ternary_i_valid&&eu_macro_ternary_i_ready)begin
        ternary_data                          <= {operand_0[REG_WIDTH-1:DATA_WIDTH],operand_ternary};
    end
end


endmodule
