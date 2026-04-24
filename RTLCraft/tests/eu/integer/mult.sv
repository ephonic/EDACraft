module mult (
    input wire clk,                      // Clock signal
    input wire rst_n,                    // Active low reset signal
    input wire valid_i,                  // Input valid signal
    output reg ready_o,                  // Ready to accept new inputs
    input wire [ISA_BITS+2*REG_WIDTH+1-1:0] mul_full_in,  
    output logic [ISA_BITS+REG_WIDTH+1-1:0] mul_full_out,
    input  [3:0] mul_vm_id_in,
    output [3:0] mul_vm_id_out,
    output reg valid_o,                  // Indicates multiplication completion
    input wire ready_i                   // Ready to accept output
);
//generate oprand_a and operand_b
logic signed_mode;              // 1: Signed mul, 0: Unsigned mul
logic [127:0] multiplicand;        // 128-bit operand A
logic [127:0] multiplier;        // 128-bit operand B
logic [127:0] product;              // 128-bit product result
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

assign {int_and_isa,int_and_cc_value,int_and_data_y,int_and_data_x} = mul_full_in;
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
assign multiplicand=  (flag_bits==3'h0 && signed_mode == 1'b1) ? {{120{1'b0}},int_and_data_x[7:0]} :
                    (flag_bits==3'h0 && signed_mode == 1'b0) ? {{120{1'b1}},int_and_data_x[7:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b1) ? {{112{1'b0}},int_and_data_x[15:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b0) ? {{112{1'b1}},int_and_data_x[15:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b1) ? {{96{1'b0}},int_and_data_x[31:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b0) ? {{96{1'b1}},int_and_data_x[31:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b1) ? {{64{1'b0}},int_and_data_x[63:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b0) ? {{64{1'b1}},int_and_data_x[63:0]} :
                    (flag_bits==3'h4 && signed_mode == 1'b1) ? int_and_data_x[127:0] :
                    (flag_bits==3'h4 && signed_mode == 1'b0) ? int_and_data_x[127:0] : 'd0;
                                                         
 assign multiplier = (flag_bits==3'h0 && signed_mode == 1'b1) ? {{120{1'b0}},int_and_data_y[7:0]} :
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
logic [ISA_BITS+2*REG_WIDTH+1-1:0] mul_full_stage1, mul_full_stage2, mul_full_stage3, mul_full_stage4, mul_full_in_delay;
logic [3:0] vm_id_stage1, vm_id_stage2, vm_id_stage3, vm_id_stage4, mul_vm_id_in_delay;


    // Pipeline stage 1 registers (input capture and sign adjustment)
    wire [127:0] stage1_multiplicand, stage1_multiplier;
    reg [127:0] abs_multiplicand, abs_multiplier;
    reg multiplicand_sign, multiplier_sign, product_sign;
    reg signed_mode_reg_stage1;
    reg valid_stage1;
    reg ready_stage1;

    // Pipeline stage 2 registers (partial multiplication)
    reg [255:0] stage2_product;
    reg signed_mode_reg_stage2;
    reg product_sign_stage2;
    reg valid_stage2;
    reg ready_stage2;

    // Pipeline stage 3 registers (sign correction)
    reg [127:0] stage3_product; // Only store the lower 128 bits
    reg product_sign_stage3;
    reg valid_stage3;
    reg ready_stage3;
    
    //
    reg ready_stage4;

    // Stage 1: Capture inputs and handle signed adjustments with handshake control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            abs_multiplicand <= 128'b0;
            abs_multiplier <= 128'b0;
            product_sign <= 0;
            signed_mode_reg_stage1 <= 0;
            valid_stage1 <= 0;
            mul_full_stage1 <= 0;
            vm_id_stage1 <= 0;
        end else if (valid_i && ready_stage1) begin
            mul_full_stage1 <= mul_full_in;
            vm_id_stage1 <= mul_vm_id_in;
            signed_mode_reg_stage1 <= signed_mode;
            valid_stage1 <= 1;
            if (signed_mode) begin
                abs_multiplicand <= multiplicand[127] ? (~multiplicand + 1) : multiplicand;
                abs_multiplier <= multiplier[127] ? (~multiplier + 1) : multiplier;
                product_sign <= multiplicand[127] ^ multiplier[127];
            end else begin
                abs_multiplicand <= multiplicand;
                abs_multiplier <= multiplier;
                product_sign <= 0;
            end
        end else if (ready_stage2) begin
            valid_stage1 <= 0; // Clear valid once stage 2 accepts data
        end
    end

    assign stage1_multiplicand = abs_multiplicand;
    assign stage1_multiplier = abs_multiplier;

    // Control ready_o signal
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ready_o <= 1;
        end else begin
            ready_o <= ready_stage1;
        end
    end

    // Stage 2: Perform unsigned multiplication with handshake control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage2_product <= 256'b0;
            signed_mode_reg_stage2 <= 0;
            product_sign_stage2 <= 0;
            valid_stage2 <= 0;
            mul_full_stage2 <= 0;
            vm_id_stage2 <= 0;
        end else if (valid_stage1 && ready_stage2) begin
            mul_full_stage2 <= mul_full_stage1;
            vm_id_stage2 <= vm_id_stage1;
            stage2_product <= stage1_multiplicand * stage1_multiplier;
            signed_mode_reg_stage2 <= signed_mode_reg_stage1;
            product_sign_stage2 <= product_sign;
            valid_stage2 <= 1;
        end else if (ready_stage3) begin
            valid_stage2 <= 0; // Clear valid once stage 3 accepts data
        end
    end

    // Stage 3: Apply sign correction if needed with handshake control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage3_product <= 128'b0;
            product_sign_stage3 <= 0;
            valid_stage3 <= 0;
            mul_full_stage3 <= 0;
            vm_id_stage3 <= 0;
        end else if (valid_stage2 && ready_stage3) begin
            if (signed_mode_reg_stage2 && product_sign_stage2) begin
                // Take the lower 128 bits and apply two's complement if negative
                stage3_product <= ~stage2_product[127:0] + 1;
            end else begin
                stage3_product <= stage2_product[127:0]; // Truncate to 128 bits
            end
            product_sign_stage3 <= product_sign_stage2;
            valid_stage3 <= 1;
            mul_full_stage3 <= mul_full_stage2;
            vm_id_stage3 <= vm_id_stage2;
        end else if (ready_stage4) begin
            valid_stage3 <= 0; // Clear valid once output is accepted
        end
    end

    // Output stage: Capture final product and valid signal with handshake control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            product <= 128'b0;
            valid_o <= 0;
            mul_full_stage4 <= 0;
            vm_id_stage4 <= 0;
        end else if (valid_stage3 && ready_stage4) begin
            product <= stage3_product;
            valid_o <= 1;
            mul_full_stage4 <= mul_full_stage3;
            vm_id_stage4 <= vm_id_stage3;
        end else if (ready_i) begin
            valid_o <= 0; // Clear valid once output is accepted
        end
    end

    // Ready signal generation for each stage
    assign ready_stage1 = !valid_stage1 || ready_stage2;
    assign ready_stage2 = !valid_stage2 || ready_stage3;
    assign ready_stage3 = !valid_stage3 || ready_stage4;
    assign ready_stage4 = !valid_o      || ready_i;

logic[REG_WIDTH-1:0] int_and_data_x_delay;
logic[REG_WIDTH-1:0] int_and_data_y_delay;
logic[ISA_BITS-1 :0] int_and_isa_delay;
logic int_and_cc_value_delay;
logic[127:0] res_valid_bits;
logic [ISA_SRC0_FMT_BITS-2:0] flag_bits_delay;   
logic signed_mode_delay; 
assign {int_and_isa_delay,int_and_cc_value_delay,int_and_data_y_delay,int_and_data_x_delay} = mul_full_in_delay;
assign flag_bits_delay = int_and_isa_delay[25:23];
assign signed_mode_delay = int_and_isa_delay[23];

assign res_valid_bits = (flag_bits_delay==3'h0 && signed_mode_delay == 1'b1) ? {{120{1'b0}},product[7:0]} :
                        (flag_bits_delay==3'h0 && signed_mode_delay == 1'b0) ? {{120{1'b1}},product[7:0]} :
                        (flag_bits_delay==3'h1 && signed_mode_delay == 1'b1) ? {{112{1'b0}},product[15:0]} :
                        (flag_bits_delay==3'h1 && signed_mode_delay == 1'b0) ? {{112{1'b1}},product[15:0]} :
                        (flag_bits_delay==3'h2 && signed_mode_delay == 1'b1) ? {{96{1'b0}},product[31:0]} :
                        (flag_bits_delay==3'h2 && signed_mode_delay == 1'b0) ? {{96{1'b1}},product[31:0]} :
                        (flag_bits_delay==3'h3 && signed_mode_delay == 1'b1) ? {{64{1'b0}},product[63:0]} :
                        (flag_bits_delay==3'h3 && signed_mode_delay == 1'b0) ? {{64{1'b1}},product[63:0]} :
                        (flag_bits_delay==3'h4 && signed_mode_delay == 1'b1) ? product[127:0] :
                        (flag_bits_delay==3'h4 && signed_mode_delay == 1'b0) ? product[127:0] : 'd0;
                                                                           
assign mul_full_in_delay = mul_full_stage4;
assign mul_vm_id_in_delay = vm_id_stage4;

assign mul_full_out = {mul_full_in_delay[ISA_BITS+2*REG_WIDTH+1-1-:ISA_BITS+1] ,{(REG_WIDTH-128){1'b0}}, res_valid_bits};
assign mul_vm_id_out = mul_vm_id_in_delay;

endmodule
