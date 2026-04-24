
module js_vm_logical (
    clk,
    rstn,
    sq_logic_data,
    sq_logic_i_valid,
    sq_logic_i_vm_id,
    sq_logic_o_ready,
    sq_logic_i_ready,
    sq_logic_o_valid,
    sq_logic_o_vm_id,
    sq_logic_res,
    logic_sq_fc_dec,
    logic_sq_fc_dec_vm_id
);
`include "js_vm.vh"
input                                        clk;
input                                        rstn;
input           [ISA_BITS+2*REG_WIDTH+1-1:0] sq_logic_data;
input                                        sq_logic_i_valid;
input           [3:0]                        sq_logic_i_vm_id;
input                                        sq_logic_o_ready;
output logic                                 sq_logic_i_ready;
output logic                                 sq_logic_o_valid;
output logic    [3:0]                        sq_logic_o_vm_id;
output logic    [ISA_BITS+REG_WIDTH+1-1:0]   sq_logic_res;
output logic    [FC_NUM-1:0]                        logic_sq_fc_dec;
output  logic   [3:0]                        logic_sq_fc_dec_vm_id;
logic [ISA_BITS-1:0] sq_logic_isa;
logic sq_logic_cc_value;
logic [REG_WIDTH-1:0] sq_logic_data_y;
logic [REG_WIDTH-1:0] sq_logic_data_x;
logic [DATA_WIDTH-1:0] truncate_window;
logic [2:0] opcode;
logic [7:0] src0_imm;
logic [REG_WIDTH-1:0] logic_data_y;
logic [REG_WIDTH-1:0] logic_data_x;
assign {sq_logic_isa,
        sq_logic_cc_value,
        logic_data_y,
        logic_data_x} = sq_logic_data;
assign  sq_logic_data_y = sq_logic_i_valid ? logic_data_y : 'b0;
assign  sq_logic_data_x = sq_logic_i_valid ? logic_data_x : 'b0;
assign opcode = sq_logic_isa[5:3];
assign src0_imm = sq_logic_isa[33:26];
// extend x and y to DATA_WIDTH(253) bits
genvar i;
generate
    for (i=0; i<DATA_WIDTH; i=i+1) begin
        always @(*) begin
            truncate_window[i] = (i<src0_imm) ? 1'b1 : 1'b0;
        end
    end
endgenerate

// calculation result
logic [DATA_WIDTH-1:0] result;
always @* begin
    case(opcode)
    OPCODE_LXOR:    result = (sq_logic_data_x[DATA_WIDTH-1:0]      != sq_logic_data_y[DATA_WIDTH-1:0]) ? 1 : 0;
    OPCODE_LAND:    result = (sq_logic_data_x[DATA_WIDTH-1:0] == 1 && sq_logic_data_y[DATA_WIDTH-1:0] == 1) ? 1 : 0;
    OPCODE_LOR:     result = (sq_logic_data_x[DATA_WIDTH-1:0] == 1 || sq_logic_data_y[DATA_WIDTH-1:0] == 1) ? 1 : 0;
    OPCODE_LNAND:   result = (sq_logic_data_x[DATA_WIDTH-1:0] == 1 && sq_logic_data_y[DATA_WIDTH-1:0] == 1) ? 0 : 1;
    OPCODE_LNOR:    result = (sq_logic_data_x[DATA_WIDTH-1:0] == 1 || sq_logic_data_y[DATA_WIDTH-1:0] == 1) ? 0 : 1;
    OPCODE_TERNARY: result = (sq_logic_cc_value > 0) ? sq_logic_data_x[DATA_WIDTH-1:0] : sq_logic_data_y[DATA_WIDTH-1:0];
    OPCODE_SHIFT:   result = sq_logic_data_x[DATA_WIDTH-1:0] >> src0_imm;
    OPCODE_TRUNCATE:result = sq_logic_data_x[DATA_WIDTH-1:0] & truncate_window;
    default:        result = 0;
    endcase
end

// output
//assign logic_sq_fc_dec  = sq_logic_res[2*REG_WIDTH+1+7+:2];
assign sq_logic_i_ready = !sq_logic_o_valid | sq_logic_o_ready;
always_ff @(posedge clk or negedge rstn) begin
    if(!rstn) begin
        sq_logic_o_valid <= 0;
    end
    else if(sq_logic_i_ready) begin
        sq_logic_o_valid <= sq_logic_i_valid;
    end
end
always_ff @(posedge clk or negedge rstn) begin
    if(!rstn) begin
        sq_logic_o_vm_id <= 0;
        sq_logic_res <= 0;
    end
    else if(sq_logic_i_ready && sq_logic_i_valid) begin
        sq_logic_o_vm_id <= sq_logic_i_vm_id;
        sq_logic_res <= {sq_logic_isa, sq_logic_cc_value, {{(REG_WIDTH-DATA_WIDTH){1'b0}},result}};
    end
end
wire    [FC_NUM-1:0]    sf = get_sf(sq_logic_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS]);
wire    [FC_NUM-1:0]    fc_dec = {FC_NUM{(sq_logic_o_valid & sq_logic_o_ready)}} & sf;
/*
always @(posedge clk or negedge rstn)
if(!rstn) begin
    logic_sq_fc_dec <= 2'b00;
    logic_sq_fc_dec_vm_id   <= 4'b0;
end else begin
    logic_sq_fc_dec <= fc_dec;
    logic_sq_fc_dec_vm_id   <= sq_logic_o_vm_id;
end
*/
always @* begin
    logic_sq_fc_dec = fc_dec;
    logic_sq_fc_dec_vm_id   = sq_logic_o_vm_id;
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
reg     [ISA_RSV_EXT_BITS-1:0]      rsv;

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
