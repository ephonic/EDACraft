//`include "js_vm.vh"

module js_vm_macro_and (
    clk,
    rstn,
    eu_macro_and_data,
    eu_macro_and_i_valid,
    eu_macro_and_i_vm_id,
    eu_macro_and_o_ready,
    eu_macro_and_i_ready,
    eu_macro_and_o_valid,
    eu_macro_and_o_vm_id,
    eu_macro_and_res
);
    
    `include "js_vm.vh"
    input                                        clk;
    input                                        rstn;
    input          [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_and_data;
    input                                        eu_macro_and_i_valid;
    input          [3:0]                         eu_macro_and_i_vm_id;
    input                                        eu_macro_and_o_ready;
    output logic                                 eu_macro_and_i_ready;
    output logic                                 eu_macro_and_o_valid;
    output logic   [3:0]                         eu_macro_and_o_vm_id;
    output logic   [ISA_BITS+REG_WIDTH+1-1:0]    eu_macro_and_res;
    logic [REG_WIDTH-1            :0] eu_macro_and_data_x;
    logic [REG_WIDTH-1            :0] eu_macro_and_data_y;
    logic [ISA_BITS-1             :0] eu_macro_and_isa;
    logic                             eu_macro_and_cc_value;
    logic [DATA_WIDTH-1           :0] eu_macro_and_data_tmp;
    logic [DATA_WIDTH-1           :0] eu_macro_and_res_tmp;
    logic                             eu_pipe_en;
    logic   [ISA_OPTYPE_BITS-1:0]       optype;
    logic   [ISA_OPCODE_BITS-1:0]       opcode;
    logic   [ISA_CC_BITS-1:0]           cc_reg;
    logic   [ISA_SF_BITS-1:0]           sf;
    logic   [ISA_WF_BITS-1:0]           wf;
    logic   [ISA_SRC0_REG_BITS-1:0]     src0_reg;
    logic   [ISA_SRC0_TYPE_BITS-1:0]    src0_type;
    logic   [ISA_SRC0_FMT_BITS-1:0]     src0_fmt;
    logic   [ISA_SRC0_IMM_BITS-1:0]     src0_imm;
    logic   [ISA_SRC1_REG_BITS-1:0]     src1_reg;
    logic   [ISA_SRC1_TYPE_BITS-1:0]    src1_type;
    logic   [ISA_SRC1_FMT_BITS-1:0]     src1_fmt;
    logic   [ISA_SRC1_IMM_BITS-1:0]     src1_imm;
    logic   [ISA_DST0_REG_BITS-1:0]     dst0_reg;
    logic   [ISA_DST1_REG_BITS-1:0]     dst1_reg;
    logic   [ISA_DST_TYPE_BITS-1:0]     dst_type;
    logic   [ISA_DST_FMT_BITS-1:0]      dst_fmt;
    logic   [ISA_RSV_BITS-1:0]          rsv;
    logic   [ISA_SRC0_IMM_BITS-1:0]     bit_nums;
    assign {eu_macro_and_isa, 
            eu_macro_and_cc_value, 
            eu_macro_and_data_y, 
            eu_macro_and_data_x} = eu_macro_and_data;
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
            } = eu_macro_and_isa;            
    assign eu_macro_and_data_tmp = eu_macro_and_data_y[DATA_WIDTH-1:0] & eu_macro_and_data_x[DATA_WIDTH-1:0];
    assign eu_pipe_en            = eu_macro_and_i_valid & eu_macro_and_i_ready;
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
                eu_macro_and_res_tmp[i] = (i<bit_nums) ? eu_macro_and_data_tmp[i]: 1'b0;
            end
        end
    endgenerate
    
    always @ (posedge clk) begin
        if (eu_pipe_en) begin
            eu_macro_and_res     <= {eu_macro_and_isa, eu_macro_and_cc_value, {(REG_WIDTH-DATA_WIDTH){1'b0}}, eu_macro_and_res_tmp};
            eu_macro_and_o_vm_id <= eu_macro_and_i_vm_id;
        end
    end
    ////handshake 
    assign eu_macro_and_i_ready = !eu_macro_and_o_valid | eu_macro_and_o_ready;
    always @ (posedge clk or negedge rstn) begin
        if (!rstn)
            eu_macro_and_o_valid <= 0;
        else if (eu_macro_and_i_ready)
            eu_macro_and_o_valid <= eu_macro_and_i_valid;
        else
            eu_macro_and_o_valid <= eu_macro_and_o_valid;
    end
    
    
    
endmodule
    
    
