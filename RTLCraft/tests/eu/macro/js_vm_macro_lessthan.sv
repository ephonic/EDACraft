//`include "js_vm.vh"

module js_vm_macro_lessthan (
    clk,
    rstn,
    eu_macro_lessthan_data,
    eu_macro_lessthan_i_valid,
    eu_macro_lessthan_i_vm_id,
    eu_macro_lessthan_o_ready,
    eu_macro_lessthan_i_ready,
    eu_macro_lessthan_o_valid,
    eu_macro_lessthan_o_vm_id,
    eu_macro_lessthan_o_mask,
    eu_macro_lessthan_res
);
    `include "js_vm.vh"
    
    localparam  DELAY  = 8;
    localparam  SEGMENT= (DATA_WIDTH+DELAY-1)/DELAY; //ceil
    localparam  BIT1   = 3'h0;
    localparam  BIT8   = 3'h1;
    localparam  BIT16  = 3'h2;
    localparam  BIT32  = 3'h3;
    localparam  BIT64  = 3'h4;
    localparam  BIT128 = 3'h5;
    localparam  BIT253 = 3'h6;
    localparam  BITMULTI = 3'h7;
    input                                        clk;
    input                                        rstn;
    input          [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_lessthan_data;
    input                                        eu_macro_lessthan_i_valid;
    input          [3:0]                         eu_macro_lessthan_i_vm_id;
    input                                        eu_macro_lessthan_o_ready;
    output logic                                 eu_macro_lessthan_i_ready;
    output logic                                 eu_macro_lessthan_o_valid;
    output logic   [3:0]                         eu_macro_lessthan_o_vm_id;
    output logic   [1:0]                         eu_macro_lessthan_o_mask;
    output logic   [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_lessthan_res;


    logic [REG_WIDTH-1            :0] eu_macro_lessthan_data_x;
    logic [REG_WIDTH-1            :0] eu_macro_lessthan_data_y;
    logic [ISA_BITS-1             :0] eu_macro_lessthan_isa;
    logic                             eu_macro_lessthan_cc_value;
    logic [DELAY*SEGMENT-1        :0] eu_macro_lessthan_condition;
    logic [                     2 :0] valid_width;
    logic [                     7 :0] multi_width;
    logic [                     7 :0] src1_multi_width;
    logic [ISA_BITS-1             :0] eu_macro_lessthan_isa_r [DELAY-1:0];
    logic                             eu_macro_lessthan_cc_value_r [DELAY-1:0];
    logic [3                      :0] eu_macro_lessthan_vm_id_r [DELAY-1:0];
    logic [DELAY*SEGMENT-1        :0] eu_macro_lessthan_data_y_r [DELAY-1:0];
    logic [DELAY*SEGMENT-1        :0] eu_macro_lessthan_condition_r [DELAY-1:0];
    logic [DELAY*SEGMENT-1        :0] eu_macro_lessthan_tmp [DELAY-1:0];
    logic [DELAY*SEGMENT-1        :0] eu_macro_lessthan_tmp_r[DELAY-1:0];
    logic [                     1 :0] mask_r           [DELAY-1:0];
    logic [                     1 :0] mask          ;
    logic [DELAY-1                :0] eu_pipe_en;
    logic [DELAY-1                :0] eu_pipe_i_valid;
    logic [DELAY-1                :0] eu_pipe_o_valid;
    logic [DELAY-1                :0] eu_pipe_i_ready;
    logic [DELAY-1                :0] eu_pipe_o_ready;
    logic [2*DATA_WIDTH-1         :0] res_tmp;
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
    
    assign {eu_macro_lessthan_isa, 
            eu_macro_lessthan_cc_value, 
            eu_macro_lessthan_data_y, 
            eu_macro_lessthan_data_x} = eu_macro_lessthan_data;
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
            } = eu_macro_lessthan_isa_r[DELAY-1];
    assign bit_nums              = src0_fmt=='d10 ? src0_imm :
                                   src0_fmt=='d0 || src0_fmt=='d1 ? 'd8 :
                                   src0_fmt=='d2 || src0_fmt=='d3 ? 'd16:
                                   src0_fmt=='d4 || src0_fmt=='d5 ? 'd32:
                                   src0_fmt=='d6 || src0_fmt=='d7 ? 'd64:
                                   src0_fmt=='d8 || src0_fmt=='d9 ? 'd128 : 'd0;
    
    assign eu_macro_lessthan_condition= {{(DELAY*SEGMENT-DATA_WIDTH){1'b0}},eu_macro_lessthan_data_y[DATA_WIDTH-1:0]} ^ {{(DELAY*SEGMENT-DATA_WIDTH){1'b0}},eu_macro_lessthan_data_x[DATA_WIDTH-1:0]};
    assign eu_macro_lessthan_i_ready  = eu_pipe_i_ready[0];
    assign eu_macro_lessthan_o_valid  = eu_pipe_o_valid[DELAY-1];
    assign eu_macro_lessthan_o_vm_id  = eu_macro_lessthan_vm_id_r[DELAY-1];
    assign eu_macro_lessthan_res      = {eu_macro_lessthan_isa_r[DELAY-1], eu_macro_lessthan_cc_value_r[DELAY-1], {(REG_WIDTH-DATA_WIDTH){1'b0}}, res_tmp[2*DATA_WIDTH-1:DATA_WIDTH], {(REG_WIDTH-DATA_WIDTH){1'b0}}, res_tmp[DATA_WIDTH-1:0]};
    assign eu_macro_lessthan_o_mask   = bit_nums > 126 ? 2'b11 : 2'b01;
    genvar i;
    generate
        for (i=0; i<DATA_WIDTH; i=i+1) begin: res_mix
            assign res_tmp[2*i]   = (i<bit_nums) ? eu_macro_lessthan_condition_r[DELAY-1][i] : 1'b0;
            assign res_tmp[2*i+1] = (i<bit_nums) ? eu_macro_lessthan_tmp_r[DELAY-1][i] : 1'b0;
        end
    endgenerate
    genvar dly;
    integer seg;
    generate
        for (dly=0; dly<DELAY; dly=dly+1) begin: lessthan_chain_block
            //handshake
            if (dly == 0) begin
                assign eu_pipe_i_valid[dly] = eu_macro_lessthan_i_valid;
                assign eu_pipe_o_ready[dly] = eu_pipe_i_ready[dly+1];
            end
            else if (dly == DELAY -1 ) begin
                assign eu_pipe_i_valid[dly] = eu_pipe_o_valid[dly-1];
                assign eu_pipe_o_ready[dly] = eu_macro_lessthan_o_ready;
            end
            else begin
                assign eu_pipe_i_valid[dly] = eu_pipe_o_valid[dly-1];
                assign eu_pipe_o_ready[dly] = eu_pipe_i_ready[dly+1];
            end
            assign eu_pipe_en[dly] = eu_pipe_i_valid[dly] &  eu_pipe_i_ready[dly];
            assign eu_pipe_i_ready[dly] = !eu_pipe_o_valid[dly] | eu_pipe_o_ready[dly];
            always @ (posedge clk or negedge rstn) begin
                if (!rstn)
                    eu_pipe_o_valid[dly] <= 0;
                else if (eu_pipe_i_ready[dly])
                    eu_pipe_o_valid[dly] <= eu_pipe_i_valid[dly];
                else
                    eu_pipe_o_valid[dly] <= eu_pipe_o_valid[dly];
            end
            
            //less than

            if (dly==0) begin
                always @ (*) begin
                    eu_macro_lessthan_tmp[dly] = 0;
                    eu_macro_lessthan_tmp[dly][dly*SEGMENT] =  eu_macro_lessthan_condition[dly*SEGMENT] & eu_macro_lessthan_data_y[dly*SEGMENT];
                    for (seg=1; seg<SEGMENT; seg=seg+1) begin
                        eu_macro_lessthan_tmp[dly][dly*SEGMENT+seg] =  eu_macro_lessthan_condition[dly*SEGMENT+seg] ? eu_macro_lessthan_data_y[dly*SEGMENT+seg] : eu_macro_lessthan_tmp[dly][dly*SEGMENT+seg-1];
                    end
                end
                always @ (posedge clk) begin
                    if (eu_pipe_en[dly]) begin
                        eu_macro_lessthan_isa_r[dly]      <= eu_macro_lessthan_isa;
                        eu_macro_lessthan_cc_value_r[dly] <= eu_macro_lessthan_cc_value;
                        eu_macro_lessthan_vm_id_r[dly]    <= eu_macro_lessthan_i_vm_id;
                        eu_macro_lessthan_data_y_r[dly]   <= {{(DELAY*SEGMENT-DATA_WIDTH){1'b0}},eu_macro_lessthan_data_y[DATA_WIDTH-1:0]};
                        eu_macro_lessthan_condition_r[dly]<= eu_macro_lessthan_condition;
                        eu_macro_lessthan_tmp_r[dly]      <= eu_macro_lessthan_tmp[dly];
                    end
                end                
            end
            else begin
                always @ (*) begin
                    eu_macro_lessthan_tmp[dly] = eu_macro_lessthan_tmp_r[dly-1];
                    eu_macro_lessthan_tmp[dly][dly*SEGMENT] =  eu_macro_lessthan_condition_r[dly-1][dly*SEGMENT] ? eu_macro_lessthan_data_y_r[dly-1][dly*SEGMENT] : eu_macro_lessthan_tmp_r[dly-1][dly*SEGMENT-1];
                    for (seg=1; seg<SEGMENT; seg=seg+1) begin
                        eu_macro_lessthan_tmp[dly][dly*SEGMENT+seg] =  eu_macro_lessthan_condition_r[dly-1][dly*SEGMENT+seg] ? eu_macro_lessthan_data_y_r[dly-1][dly*SEGMENT+seg] : eu_macro_lessthan_tmp[dly][dly*SEGMENT+seg-1];
                    end
                end
            
                always @ (posedge clk) begin
                    if (eu_pipe_en[dly]) begin
                        eu_macro_lessthan_isa_r[dly]      <= eu_macro_lessthan_isa_r[dly-1];
                        eu_macro_lessthan_cc_value_r[dly] <= eu_macro_lessthan_cc_value_r[dly-1];
                        eu_macro_lessthan_vm_id_r[dly]    <= eu_macro_lessthan_vm_id_r[dly-1];
                        eu_macro_lessthan_data_y_r[dly]   <= eu_macro_lessthan_data_y_r[dly-1];
                        eu_macro_lessthan_condition_r[dly]<= eu_macro_lessthan_condition_r[dly-1];
                        eu_macro_lessthan_tmp_r[dly]      <= eu_macro_lessthan_tmp[dly];
                    end
                end
            end
        end
    endgenerate


    
    
    
endmodule
    
    
