`include "js_vm.vh"
module add (
    input wire clk,                      // Clock signal
    input wire rst_n,                    // Active low reset signal
    input wire valid_i,                  // Input valid signal
    output reg ready_o,                  // Ready to accept new inputs
    output reg valid_o,                  // Indicates addition completion
    input wire ready_i,                   // Ready to accept output
    input wire [ISA_BITS+2*REG_WIDTH+1-1:0] add_full_in,  
    output logic [ISA_BITS+REG_WIDTH+1-1:0] add_full_out,
    input  [3:0] add_vm_id_in,
    output [3:0] add_vm_id_out
);

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
logic[REG_WIDTH-1:0] int_and_data_x;
logic[REG_WIDTH-1:0] int_and_data_y;
logic[ISA_BITS-1 :0] int_and_isa;
logic int_and_cc_value;
logic [ISA_SRC0_FMT_BITS-2:0] flag_bits;

assign {int_and_isa,int_and_cc_value,int_and_data_y,int_and_data_x} = add_full_in;
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
        } = int_and_isa;
assign flag_bits   = src0_fmt[ISA_SRC0_FMT_BITS-1:1];
assign signed_mode = src0_fmt[0];

assign operand_a =  (flag_bits==3'h0 && signed_mode == 1'b1) ? {{120{1'b0}},int_and_data_x[7:0]} :
                    (flag_bits==3'h0 && signed_mode == 1'b0) ? {{120{1'b1}},int_and_data_x[7:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b1) ? {{112{1'b0}},int_and_data_x[15:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b0) ? {{112{1'b1}},int_and_data_x[15:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b1) ? {{96{1'b0}},int_and_data_x[31:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b0) ? {{96{1'b1}},int_and_data_x[31:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b1) ? {{64{1'b0}},int_and_data_x[63:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b0) ? {{64{1'b1}},int_and_data_x[63:0]} :
                    (flag_bits==3'h4 && signed_mode == 1'b1) ? int_and_data_x[127:0] :
                    (flag_bits==3'h4 && signed_mode == 1'b0) ? int_and_data_x[127:0] : 'd0;
                                                         
 assign operand_b = (flag_bits==3'h0 && signed_mode == 1'b1) ? {{120{1'b0}},int_and_data_y[7:0]} :
                    (flag_bits==3'h0 && signed_mode == 1'b0) ? {{120{1'b1}},int_and_data_y[7:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b1) ? {{112{1'b0}},int_and_data_y[15:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b0) ? {{112{1'b1}},int_and_data_y[15:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b1) ? {{96{1'b0}},int_and_data_y[31:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b0) ? {{96{1'b1}},int_and_data_y[31:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b1) ? {{64{1'b0}},int_and_data_y[63:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b0) ? {{64{1'b1}},int_and_data_y[63:0]} :
                    (flag_bits==3'h4 && signed_mode == 1'b1) ? int_and_data_y[127:0] :
                    (flag_bits==3'h4 && signed_mode == 1'b0) ? int_and_data_y[127:0] : 'd0;

//delay in pipeline
logic [ISA_BITS+2*REG_WIDTH+1-1:0] add_full_stage1, add_full_stage2, add_full_stage3, add_full_in_delay;
logic [3:0] vm_id_stage1, vm_id_stage2, vm_id_stage3, add_vm_id_in_delay;


    // Pipeline stage 1 registers
    reg [127:0] stage1_operand_a, stage1_operand_b;
    reg signed_mode_reg_stage1;
    reg valid_stage1;
    reg ready_stage1;

    // Pipeline stage 2 registers
    reg [127:0] stage2_sum;
    reg stage2_carry;
    reg signed_mode_reg_stage2;
    reg operand_a_sign, operand_b_sign;
    reg valid_stage2;
    reg ready_stage2;

    // Pipeline stage 3 registers
    reg sum_sign_stage2;
    reg valid_stage3;
    reg ready_stage3;

    // Stage 1: Capture inputs with handshake control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage1_operand_a <= 128'b0;
            stage1_operand_b <= 128'b0;
            signed_mode_reg_stage1 <= 0;
            valid_stage1 <= 0;
            add_full_stage1 <= 0;
            vm_id_stage1 <= 0;
        end else if (ready_stage1 && valid_i) begin
            // Load inputs into stage 1 registers
            stage1_operand_a <= operand_a;
            stage1_operand_b <= operand_b;
            signed_mode_reg_stage1 <= signed_mode;
            valid_stage1 <= 1;
            add_full_stage1 <= add_full_in;
            vm_id_stage1 <= add_vm_id_in;
        end else if (ready_stage2) begin
            valid_stage1 <= 0; // Clear valid once stage 2 accepts data
        end
    end

    // Control ready_o signal
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ready_o <= 1;
        end else begin
            ready_o <= ready_stage1;
        end
    end

    // Stage 2: Perform addition with handshake control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage2_sum <= 128'b0;
            stage2_carry <= 0;
            signed_mode_reg_stage2 <= 0;
            operand_a_sign <= 0;
            operand_b_sign <= 0;
            valid_stage2 <= 0;
            add_full_stage2 <= 0;
            vm_id_stage2 <= 0;
        end else if (valid_stage1 && ready_stage2) begin
            // Capture inputs from stage 1
            signed_mode_reg_stage2 <= signed_mode_reg_stage1;
            operand_a_sign <= stage1_operand_a[127];
            operand_b_sign <= stage1_operand_b[127];

            // Perform addition
            {stage2_carry, stage2_sum} <= stage1_operand_a + stage1_operand_b;
            valid_stage2 <= 1;

            add_full_stage2 <= add_full_stage1;
            vm_id_stage2 <= vm_id_stage1;
        end else if (ready_stage3) begin
            valid_stage2 <= 0; // Clear valid once stage 3 accepts data
        end
    end

    // Stage 3: Adjust sum for signed addition if necessary
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sum <= 128'b0;
            valid_o <= 0;
            add_full_stage3 <= 0;
            vm_id_stage3 <= 0;
        end else if (valid_stage2 && ready_stage3) begin
            // Capture results from stage 2
            add_full_stage3 <= add_full_stage2;
            vm_id_stage3 <= vm_id_stage2;
            sum <= stage2_sum;
            valid_o <= 1;

            // Adjust sign for signed addition
            if (signed_mode_reg_stage2) begin
                // If overflow occurred, adjust the sign bit to match expected result
                if ((operand_a_sign == operand_b_sign) && (operand_a_sign != stage2_sum[127])) begin
                    sum[127] <= operand_a_sign; // Correct sign bit
                end
            end
        end else if (ready_i) begin
            valid_o <= 0; // Clear valid once output is accepted
        end
    end

    // Ready signal generation for each stage
    assign ready_stage1 = !valid_stage1 || ready_stage2;
    assign ready_stage2 = !valid_stage2 || ready_stage3;
    assign ready_stage3 = !valid_o      || ready_i;
    
    
logic[REG_WIDTH-1:0] int_and_data_x_delay;
logic[REG_WIDTH-1:0] int_and_data_y_delay;
logic[ISA_BITS-1 :0] int_and_isa_delay;
logic[127:0] res_valid_bits;
logic int_and_cc_value_delay;
logic [ISA_SRC0_FMT_BITS-2:0] flag_bits_delay;   
logic signed_mode_delay; 
assign {int_and_isa_delay,int_and_cc_value_delay,int_and_data_y_delay,int_and_data_x_delay} = add_full_in_delay;
assign flag_bits_delay = int_and_isa_delay[25:23];
assign signed_mode_delay = int_and_isa_delay[23];

assign res_valid_bits = (flag_bits_delay==3'h0 && signed_mode_delay == 1'b1) ? {{120{1'b0}},sum[7:0]} :
                        (flag_bits_delay==3'h0 && signed_mode_delay == 1'b0) ? {{120{1'b1}},sum[7:0]} :
                        (flag_bits_delay==3'h1 && signed_mode_delay == 1'b1) ? {{112{1'b0}},sum[15:0]} :
                        (flag_bits_delay==3'h1 && signed_mode_delay == 1'b0) ? {{112{1'b1}},sum[15:0]} :
                        (flag_bits_delay==3'h2 && signed_mode_delay == 1'b1) ? {{96{1'b0}},sum[31:0]} :
                        (flag_bits_delay==3'h2 && signed_mode_delay == 1'b0) ? {{96{1'b1}},sum[31:0]} :
                        (flag_bits_delay==3'h3 && signed_mode_delay == 1'b1) ? {{64{1'b0}},sum[63:0]} :
                        (flag_bits_delay==3'h3 && signed_mode_delay == 1'b0) ? {{64{1'b1}},sum[63:0]} :
                        (flag_bits_delay==3'h4 && signed_mode_delay == 1'b1) ? sum[127:0] :
                        (flag_bits_delay==3'h4 && signed_mode_delay == 1'b0) ? sum[127:0] : 'd0;

assign add_full_in_delay = add_full_stage3;
assign add_vm_id_in_delay = vm_id_stage3;

assign add_full_out = {add_full_in_delay[ISA_BITS+2*REG_WIDTH+1-1-:ISA_BITS+1] ,{(REG_WIDTH-128){1'b0}}, res_valid_bits};
assign add_vm_id_out = add_vm_id_in_delay;

endmodule
