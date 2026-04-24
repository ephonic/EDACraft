module divider (/*AUTOARG*/
   // Outputs
   ready_o, div_full_out, div_vm_id_out, valid_o,
   // Inputs
   clk, rst_n, valid_i, div_full_in, div_vm_id_in, ready_i
   );
   `include "js_vm.vh"
    input wire clk;                       // Clock signal
    input wire rst_n;                     // Reset signal, active low
    input  valid_i;                   // Input valid signal
    output reg ready_o;                   // Ready to accept new inputs
    input wire [ISA_BITS+2*REG_WIDTH+1-1:0] div_full_in;  
    output logic [ISA_BITS+REG_WIDTH+1-1:0] div_full_out;
    input  [3:0] div_vm_id_in;
    output [3:0] div_vm_id_out;
    output reg valid_o;                   // Indicates division completion
    input  ready_i;                    // Ready to accept output

logic signed_mode_src0, signed_mode_src1;               // 1: Signed division, 0: Unsigned division
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


assign {int_and_isa,int_and_cc_value,int_and_data_y,int_and_data_x} = div_full_in;
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
assign signed_mode_src0 = src0_fmt[0];
assign signed_mode_src1 = src1_fmt[0];

wire [127:0] 	      res;
   

divider_core div_core (
    .clk(clk),
    .rst_n(rst_n),
    .valid_i(valid_i),
    .ready_o(ready_o),
    .valid_o(valid_o),
    .ready_i(ready_i),
    .flags_src0(flag_bits),
    .flags_src1(flag_bits),
    .signed_mode_src0(signed_mode_src0),
    .signed_mode_src1(signed_mode_src1),
    .src0(int_and_data_x[127:0]),
    .src1(int_and_data_y[127:0]),
    .vm_id_in(div_vm_id_in),
    .vm_id_out(div_vm_id_out),
    .div_full_in(div_full_in),
    .div_full_out(div_full_out)
);

endmodule
