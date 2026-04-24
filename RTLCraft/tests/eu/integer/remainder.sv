module remainder (
    input wire clk,                       // Clock signal
    input wire rst_n,                     // Reset signal, active low
    input  valid_i,                   // Input valid signal
    output reg ready_o,                   // Ready to accept new inputs
    input wire [ISA_BITS+2*REG_WIDTH+1-1:0] rem_full_in,  
    output logic [ISA_BITS+REG_WIDTH+1-1:0] rem_full_out,
    input  [3:0] rem_vm_id_in,
    output [3:0] rem_vm_id_out,
    output reg valid_o,                   // Indicates division completion
    input  ready_i                    // Ready to accept output
);


logic signed_mode;               // 1: Signed division, 0: Unsigned division
logic [127:0] dividend;          // 128-bit dividend
logic [127:0] divisor;           // 128-bit divisor
logic [127:0] quotient;          // 128-bit quotient
logic [127:0] remainder;         // 128-bit remainder
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
logic [REG_WIDTH-1:0] int_and_data_x;
logic [REG_WIDTH-1:0] int_and_data_y;
logic [ISA_BITS-1 :0] int_and_isa;
logic int_and_cc_value;
logic [ISA_SRC0_FMT_BITS-2:0] flag_bits;

assign {int_and_isa,int_and_cc_value,int_and_data_y,int_and_data_x} = rem_full_in;
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

assign dividend =  (flag_bits==3'h0 && signed_mode == 1'b1) ? {{120{1'b0}},int_and_data_x[7:0]} :
                    (flag_bits==3'h0 && signed_mode == 1'b0) ? {{120{1'b1}},int_and_data_x[7:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b1) ? {{112{1'b0}},int_and_data_x[15:0]} :
                    (flag_bits==3'h1 && signed_mode == 1'b0) ? {{112{1'b1}},int_and_data_x[15:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b1) ? {{96{1'b0}},int_and_data_x[31:0]} :
                    (flag_bits==3'h2 && signed_mode == 1'b0) ? {{96{1'b1}},int_and_data_x[31:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b1) ? {{64{1'b0}},int_and_data_x[63:0]} :
                    (flag_bits==3'h3 && signed_mode == 1'b0) ? {{64{1'b1}},int_and_data_x[63:0]} :
                    (flag_bits==3'h4 && signed_mode == 1'b1) ? int_and_data_x[127:0] :
                    (flag_bits==3'h4 && signed_mode == 1'b0) ? int_and_data_x[127:0] : 'd0;
                                                         
 assign divisor = (flag_bits==3'h0 && signed_mode == 1'b1) ? {{120{1'b0}},int_and_data_y[7:0]} :
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
reg [ISA_BITS+2*REG_WIDTH+1-1:0] rem_full_in_reg, rem_full_delay;
reg [3:0] rem_vm_id_in_reg, rem_vm_id_delay;

    // State machine variables
    reg [4:0] count;                      // Counter, processes 8 bits per cycle, up to 16 times
    logic [255:0] partial_remainder;        // Partial remainder, 256 bits (stores remainder and current part of dividend)
    logic [127:0] temp_quotient;            // Temporary quotient register
    logic [127:0] shifted_divisor;          // Shifted divisor for parallel 8-bit comparison
    reg done;                             // Completion flag

    // Variables for sign handling
    logic [127:0] abs_dividend, abs_divisor;

    logic quotient_sign;

    // State machine for control
    reg processing;

    // Ready signal control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ready_o <= 1;
        end else if (valid_i && ready_o) begin
            ready_o <= 0;  // Busy processing
        end else if (valid_o && ready_i) begin
            ready_o <= 1;  // Ready for new input after output is accepted
        end
    end

    // Division logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            quotient <= 128'd0;
            remainder <= 128'd0;
            valid_o <= 0;
            done <= 0;
            count <= 5'd0;
            processing <= 0;
            rem_full_in_reg <= 0;
            rem_vm_id_in_reg <= 0;
            partial_remainder <= 0;
            temp_quotient     <= 0;
            shifted_divisor   <= 0;
            rem_full_delay    <= 0;
            rem_vm_id_delay   <= 0;
        end else if (valid_i && ready_o && !processing) begin
            // Start division
            processing <= 1;
            done <= 0;
            count <= 5'd0;
            valid_o <= 0;

            rem_full_in_reg <= rem_full_in;
            rem_vm_id_in_reg <= rem_vm_id_in;

            if (divisor == 128'd0) begin
                // Handle division by zero
                quotient <= 128'd0;
                remainder <= 128'hFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF;
                valid_o <= 1;
                done <= 1;
                processing <= 0;
            end else begin
                // Initialization for division
                partial_remainder <= {128'd0, abs_dividend}; // Load dividend into lower 128 bits
                temp_quotient <= 128'd0;
                shifted_divisor <= abs_divisor << 120; 
       // Pre-shift divisor to align with the highest 8 bits
            end
        end else if (processing && !done) begin
            // Perform division step by step
            if (count <= 16) begin
                shifted_divisor <= abs_divisor << (128 - 8 * (count+1));
                // Attempt 8-bit quotient approximation
                for (integer j = 255; j >= 0; j = j - 1) begin
                    if (partial_remainder >= (shifted_divisor * j) && partial_remainder < (shifted_divisor * (j+1))) begin
                        partial_remainder <= partial_remainder - (shifted_divisor * j);
                        temp_quotient <= (temp_quotient << 8) | j[7:0];
                        //break;
                    end
                end
                count <= count + 1;
                
            end else begin
                // Complete division after 16 iterations
                done <= 1;
                processing <= 0;
                count <= 0;

                rem_full_delay <= rem_full_in_reg;
                rem_vm_id_delay <= rem_vm_id_in_reg;

                // Handle quotient and remainder sign
                quotient <= quotient_sign ? (~temp_quotient + 1) : temp_quotient;
                remainder <= dividend[127] ? (~partial_remainder[127:0] + 1) : partial_remainder[127:0];
                valid_o <= 1;
            end
        end else if (valid_o && ready_i) begin
            valid_o <= 0; // Clear valid once output is accepted
        end
    end
assign abs_dividend = signed_mode ? (dividend[127] ? (~dividend + 1) : dividend) : dividend;
assign abs_divisor = signed_mode ? (divisor[127] ? (~divisor + 1) : divisor) : divisor;
assign quotient_sign = signed_mode ? dividend[127] ^ divisor[127] : 0;

logic[REG_WIDTH-1:0] int_and_data_x_delay;
logic[REG_WIDTH-1:0] int_and_data_y_delay;
logic[ISA_BITS-1 :0] int_and_isa_delay;
logic int_and_cc_value_delay;
logic[127:0] res_valid_bits;
logic [ISA_SRC0_FMT_BITS-2:0] flag_bits_delay;   
logic signed_mode_delay; 
assign {int_and_isa_delay,int_and_cc_value_delay,int_and_data_y_delay,int_and_data_x_delay} = rem_full_delay;
assign flag_bits_delay = int_and_isa_delay[25:23];
assign signed_mode_delay = int_and_isa_delay[23];

assign res_valid_bits = (flag_bits_delay==3'h0 && signed_mode_delay == 1'b1) ? {{120{1'b0}},remainder[7:0]} :
                        (flag_bits_delay==3'h0 && signed_mode_delay == 1'b0) ? {{120{1'b1}},remainder[7:0]} :
                        (flag_bits_delay==3'h1 && signed_mode_delay == 1'b1) ? {{112{1'b0}},remainder[15:0]} :
                        (flag_bits_delay==3'h1 && signed_mode_delay == 1'b0) ? {{112{1'b1}},remainder[15:0]} :
                        (flag_bits_delay==3'h2 && signed_mode_delay == 1'b1) ? {{96{1'b0}},remainder[31:0]} :
                        (flag_bits_delay==3'h2 && signed_mode_delay == 1'b0) ? {{96{1'b1}},remainder[31:0]} :
                        (flag_bits_delay==3'h3 && signed_mode_delay == 1'b1) ? {{64{1'b0}},remainder[63:0]} :
                        (flag_bits_delay==3'h3 && signed_mode_delay == 1'b0) ? {{64{1'b1}},remainder[63:0]} :
                        (flag_bits_delay==3'h4 && signed_mode_delay == 1'b1) ? remainder[127:0] :
                        (flag_bits_delay==3'h4 && signed_mode_delay == 1'b0) ? remainder[127:0] : 'd0;



assign rem_full_out = {rem_full_delay[ISA_BITS+2*REG_WIDTH+1-1-:ISA_BITS+1] ,{(REG_WIDTH-128){1'b0}} , res_valid_bits};
assign rem_vm_id_out = rem_vm_id_delay;


endmodule
