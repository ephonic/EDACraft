
module js_vm_macro_leq (
    clk,
    rstn,
    eu_macro_leq_data,
    eu_macro_leq_i_valid,
    eu_macro_leq_i_vm_id,
    eu_macro_leq_o_ready,
    eu_macro_leq_o_valid,
    eu_macro_leq_i_ready,
    eu_macro_leq_o_vm_id,
    eu_macro_leq_variable
);

`include "js_vm.vh"
input                                  clk;
input                                  rstn;
input    [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_leq_data;
input                                  eu_macro_leq_i_valid;
input    [3:0]                         eu_macro_leq_i_vm_id;
input                                  eu_macro_leq_o_ready;
output   logic                         eu_macro_leq_o_valid;
output   logic                         eu_macro_leq_i_ready;
output   logic [3:0]                   eu_macro_leq_o_vm_id;
output   logic [ISA_BITS+REG_WIDTH:0]  eu_macro_leq_variable;
localparam PIPE_LEVEL = 16;
localparam PIPE_WIDTH = (DATA_WIDTH+PIPE_LEVEL-1)/PIPE_LEVEL;
localparam DATA_WIDTH_CEIL = PIPE_WIDTH*PIPE_LEVEL;
genvar     i;
genvar     j;
genvar     t;

reg [ISA_BITS:0]      isa_r [PIPE_LEVEL-1:0];
reg [3:0]             vm_id [PIPE_LEVEL-1:0];
reg [PIPE_LEVEL-1:0]  leq_valid;
reg [DATA_WIDTH_CEIL-1:0]  leq_data_x [PIPE_LEVEL-1:0];
reg [DATA_WIDTH_CEIL-1:0]  leq_data_y [PIPE_LEVEL-1:0];
reg [DATA_WIDTH_CEIL-1:0]  leq_data_res [PIPE_LEVEL-1:0];
reg [DATA_WIDTH-1:0]       leq_res_temp;
reg [DATA_WIDTH-1:0]       leq_variable_temp;
reg [7:0]                  second_zero_pos [PIPE_LEVEL-1:0];
reg [7:0]                  zero_cnt [PIPE_LEVEL-1:0];
reg [7:0]                  second_zero_pos_tmp [PIPE_LEVEL-1:0];
reg [7:0]                  zero_cnt_tmp [PIPE_LEVEL-1:0];

reg [REG_WIDTH-DATA_WIDTH-1:0] leq_data_flag [PIPE_LEVEL-1:0];
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

wire[PIPE_WIDTH-1:0]  leq_data_logic [PIPE_LEVEL-1:0];

wire[DATA_WIDTH-1:0]  leq_x_init;
wire[DATA_WIDTH-1:0]  leq_y_init;
wire[PIPE_LEVEL-1:0]  leq_ready;

assign eu_macro_leq_i_ready = leq_ready[0];//eu_macro_leq_o_ready;
assign eu_macro_leq_o_vm_id   = vm_id[PIPE_LEVEL-1];
assign eu_macro_leq_variable= {isa_r[PIPE_LEVEL-1],{(REG_WIDTH-DATA_WIDTH){1'b0}},leq_res_temp};
assign eu_macro_leq_o_valid = leq_valid[PIPE_LEVEL-1];
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
        } = isa_r[PIPE_LEVEL-1][ISA_BITS:1]; 
assign bit_nums              = src0_fmt=='d10 ? src0_imm :
                               src0_fmt=='d0 || src0_fmt=='d1 ? 'd8 :
                               src0_fmt=='d2 || src0_fmt=='d3 ? 'd16:
                               src0_fmt=='d4 || src0_fmt=='d5 ? 'd32:
                               src0_fmt=='d6 || src0_fmt=='d7 ? 'd64:
                               src0_fmt=='d8 || src0_fmt=='d9 ? 'd128 : 'd0;
assign leq_y_init         = eu_macro_leq_data[2*REG_WIDTH-1:REG_WIDTH];
assign leq_x_init         = eu_macro_leq_data[REG_WIDTH-1:0];

// integer k;
// reg found_2nd_zero,found_1st_zero;
// always @* begin
//     found_1st_zero = 1'b0;
//     found_2nd_zero = 1'b0;
//     leq_res_temp  = leq_variable_temp;
//     for (k=0; k< DATA_WIDTH; k=k+1) begin
//         if(!found_1st_zero && !leq_data_y[PIPE_LEVEL-1][k]) begin
//             found_1st_zero = 1'b1;
//         end
//         else if (found_1st_zero && !found_2nd_zero && !leq_data_y[PIPE_LEVEL-1][k]) begin
//             found_2nd_zero = 1'b1;
//             leq_res_temp = leq_variable_temp>>k;
//         end
//     end
// end

assign leq_res_temp = leq_variable_temp >> second_zero_pos[PIPE_LEVEL-1];

generate
    for (i=0; i<DATA_WIDTH; i=i+1) begin
        always @(*) begin
            leq_variable_temp[i] = (i<bit_nums) ? leq_data_res[PIPE_LEVEL-1][i]: 1'b0;
        end
    end
endgenerate

generate
    for(i=0;i<PIPE_LEVEL;i=i+1)begin
        if(i==(PIPE_LEVEL-1))begin
            assign leq_ready[i] = eu_macro_leq_o_ready|| (!leq_valid[i]);
        end
        else begin
            assign leq_ready[i] = leq_ready[i+1] || (!leq_valid[i]);
        end
    end
endgenerate

generate
    for(i=0;i<PIPE_LEVEL;i=i+1)begin
        if(i==0)begin

        // zero cnt
	integer k; 
        always @(*) begin
	   zero_cnt_tmp[i] = 8'b0;
	   second_zero_pos_tmp[i] = 8'b0;
            for(k=0; k< PIPE_WIDTH; k=k+1) begin
                if(!leq_y_init[k]) begin
                    zero_cnt_tmp[i] = zero_cnt_tmp[i] + 1'b1;
                    if(zero_cnt_tmp[i]==2)begin
                        second_zero_pos_tmp[i] = k;
                    end
                end
            end
        end

        always @(posedge clk or negedge rstn) begin
            if(!rstn)begin
                zero_cnt[i]                    <= '0;
                second_zero_pos[i]             <= '0;
            end
            else if(eu_macro_leq_i_valid&&eu_macro_leq_i_ready)begin
                zero_cnt[i]                    <= zero_cnt_tmp[i];
                second_zero_pos[i]             <= second_zero_pos_tmp[i];        
            end
        end

        assign leq_data_logic[0][0] = leq_y_init[0] ? '0 : leq_x_init[0];
        for(j=1;j<PIPE_WIDTH;j=j+1)begin
            assign leq_data_logic[0][j] = leq_y_init[j] ?  leq_data_logic[0][j-1]&&leq_x_init[j] : leq_data_logic[0][j-1] || leq_x_init[j];   
        end

        always @(posedge clk or negedge rstn) begin
            if(!rstn)begin
                isa_r[i]                          <= '0;
                vm_id[i]                          <= '0;
            end
            else if(eu_macro_leq_i_valid&&eu_macro_leq_i_ready)begin
                isa_r[i]                          <= eu_macro_leq_data[ISA_BITS+2*REG_WIDTH:2*REG_WIDTH];
                vm_id[i]                          <= eu_macro_leq_i_vm_id;        
            end
        end            

        always @(posedge clk or negedge rstn) begin
            if(!rstn)begin
                leq_valid[i]                    <= '0;
            end
            else if(eu_macro_leq_i_ready)begin
                leq_valid[i]                    <= eu_macro_leq_i_valid;
            end
        end

        always @(posedge clk or negedge rstn) begin
            if(!rstn)begin
                leq_data_x[i]                   <= '0;
                leq_data_y[i]                   <= '0;
                leq_data_flag[i]                <= '0;
            end
            else if(eu_macro_leq_i_valid&&eu_macro_leq_i_ready)begin
                leq_data_x[i]                   <= leq_x_init;
                leq_data_y[i]                   <= leq_y_init;
                leq_data_flag[i]                <= eu_macro_leq_data[REG_WIDTH-1:DATA_WIDTH];
            end
        end

        for(t=0;t<PIPE_LEVEL;t=t+1)begin
            always @(posedge clk or negedge rstn) begin
                if(!rstn)begin
                    leq_data_res[i][(t+1)*PIPE_WIDTH-1:t*PIPE_WIDTH]        <= '0;
                end
                else if(eu_macro_leq_i_valid&&eu_macro_leq_i_ready)begin
                    leq_data_res[i][(t+1)*PIPE_WIDTH-1:t*PIPE_WIDTH]        <= (t==i) ? leq_data_logic[i] : '0;
                end
            end
        end

        end
        //=========================OTHER CASES========================
        else begin
        assign leq_data_logic[i][0] = leq_data_y[i-1][i*PIPE_WIDTH] ?  leq_data_res[i-1][i*PIPE_WIDTH-1]&&leq_data_x[i-1][i*PIPE_WIDTH] : leq_data_res[i-1][i*PIPE_WIDTH-1] || leq_data_x[i-1][i*PIPE_WIDTH];
        for(j=1;j<PIPE_WIDTH;j=j+1)begin
            assign leq_data_logic[i][j] = leq_data_y[i-1][i*PIPE_WIDTH+j] ?  leq_data_logic[i][j-1]&&leq_data_x[i-1][i*PIPE_WIDTH+j] : leq_data_logic[i][j-1] || leq_data_x[i-1][i*PIPE_WIDTH+j]; 
        end

        // zero cnt
	integer k;
        always @(*) begin   
            zero_cnt_tmp[i] = zero_cnt[i-1];
            second_zero_pos_tmp[i] = second_zero_pos[i-1];
            for(k=0; k< PIPE_WIDTH; k=k+1) begin
                if(!leq_data_y[i-1][i*PIPE_WIDTH+k]) begin
                    zero_cnt_tmp[i] = zero_cnt_tmp[i] + 1'b1;
                    if(zero_cnt_tmp[i]==2)begin
                        second_zero_pos_tmp[i] = i*PIPE_WIDTH + k;
                    end
                end
            end
        end

        always @(posedge clk or negedge rstn) begin
            if(!rstn)begin
                zero_cnt[i]                    <= '0;
                second_zero_pos[i]             <= '0;
            end
            else if(leq_valid[i-1]&&leq_ready[i])begin
                zero_cnt[i]                    <= zero_cnt_tmp[i];
                second_zero_pos[i]             <= second_zero_pos_tmp[i];        
            end
        end

        always @(posedge clk or negedge rstn) begin
            if(!rstn)begin
                isa_r[i]                          <= '0;
                vm_id[i]                          <= '0;
            end
            else if(leq_valid[i-1]&&leq_ready[i])begin
                isa_r[i]                          <= isa_r[i-1];
                vm_id[i]                          <= vm_id[i-1];       
            end
        end         

        always @(posedge clk or negedge rstn) begin
            if(!rstn)begin
                leq_valid[i]                    <= '0;
            end
            else if(leq_ready[i])begin
                leq_valid[i]                    <= leq_valid[i-1];
            end
        end

        always @(posedge clk or negedge rstn) begin
            if(!rstn)begin
                leq_data_x[i]                   <= '0;
                leq_data_y[i]                   <= '0;
                leq_data_flag[i]                <= '0;
            end
            else if(leq_valid[i-1]&&leq_ready[i])begin
                leq_data_x[i]                   <= leq_data_x[i-1];   
                leq_data_y[i]                   <= leq_data_y[i-1];   
                leq_data_flag[i]                <= leq_data_flag[i-1];
            end
        end


        for(t=0;t<PIPE_LEVEL;t=t+1)begin
            always @(posedge clk or negedge rstn) begin
                if(!rstn)begin
                    leq_data_res[i][(t+1)*PIPE_WIDTH-1:t*PIPE_WIDTH]        <= '0;
                end
                else if(leq_valid[i-1]&&leq_ready[i])begin
                    leq_data_res[i][(t+1)*PIPE_WIDTH-1:t*PIPE_WIDTH]        <= (t==i) ? leq_data_logic[i] : leq_data_res[i-1][(t+1)*PIPE_WIDTH-1:t*PIPE_WIDTH];
                end
            end
        end
        


        end
    end
endgenerate








endmodule
