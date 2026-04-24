//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2024/11/10 21:00:23
// Design Name: 
// Module Name: integer_compute
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module js_vm_int(
/*AUTOARG*/
   // Outputs
   int_active, int_and_i_ready, int_and_o_valid, int_and_o_vm_id,
   int_and_res, int_sq_fc_dec, int_sq_fc_dec_vm_id,
   // Inputs
   clk, rstn, int_and_data, int_and_i_valid, int_and_o_ready,
   int_and_i_vm_id
   );
`include "js_vm.vh"
input                               clk;
input                               rstn;
output                              int_active;
input  [ISA_BITS+2*REG_WIDTH+1-1:0] int_and_data;
input                               int_and_i_valid;
output logic                        int_and_i_ready;
input                               int_and_o_ready;
output logic                        int_and_o_valid;
input  [3:0]                        int_and_i_vm_id;
output logic [3:0]                  int_and_o_vm_id;
output logic [ISA_BITS+REG_WIDTH+1-1:0] int_and_res;

output logic [FC_NUM-1:0]                  int_sq_fc_dec; 
output logic [3:0]                  int_sq_fc_dec_vm_id; 
logic[REG_WIDTH-1:0] int_and_data_x;
logic[REG_WIDTH-1:0] int_and_data_y;
logic[ISA_BITS-1 :0] int_and_isa;
logic int_and_cc_value;

logic [ISA_BITS-1:0] int_and_isa_delay;
logic [3:0] int_and_i_vm_id_delay;

logic [ISA_BITS+2*REG_WIDTH+1-1:0] add_full_in;
logic [ISA_BITS+2*REG_WIDTH+1-1:0] sub_full_in;
logic [ISA_BITS+2*REG_WIDTH+1-1:0] mul_full_in;
logic [ISA_BITS+2*REG_WIDTH+1-1:0] div_full_in;
logic [ISA_BITS+2*REG_WIDTH+1-1:0] rem_full_in;

logic [ISA_BITS+REG_WIDTH+1-1:0] add_full_out;
logic [ISA_BITS+REG_WIDTH+1-1:0] sub_full_out;
logic [ISA_BITS+REG_WIDTH+1-1:0] mul_full_out;
logic [ISA_BITS+REG_WIDTH+1-1:0] div_full_out;
logic [ISA_BITS+REG_WIDTH+1-1:0] rem_full_out;
logic [3:0] vm_id_add_in;
logic [3:0] vm_id_add_out;
logic [3:0] vm_id_sub_in;
logic [3:0] vm_id_sub_out;
logic [3:0] vm_id_mul_in;
logic [3:0] vm_id_mul_out;
logic [3:0] vm_id_div_in;
logic [3:0] vm_id_div_out;
logic [3:0] vm_id_rem_in;
logic [3:0] vm_id_rem_out;
logic [3:0] vm_id_o_main;
   
wire    sync_push;
wire    sync_din;    // 0: to main, 1: to div
wire    sync_pop;      
wire    sync_dout;         // used to control if modmul result is sent to acc
wire    sync_empty;
wire    sync_full;
wire    obuf_push;
wire    [4+ISA_BITS+REG_WIDTH+1-1:0]    obuf_din; 
wire    obuf_pop;      
wire    [4+ISA_BITS+REG_WIDTH+1-1:0]    obuf_dout; 
wire    obuf_empty;
wire    obuf_full;
assign {int_and_isa,int_and_cc_value,int_and_data_y,int_and_data_x} = int_and_data;

assign add_full_in = int_and_data;
assign sub_full_in = int_and_data;
assign mul_full_in = int_and_data;
assign div_full_in = int_and_data;
assign rem_full_in = int_and_data;

assign vm_id_add_in = int_and_i_vm_id;
assign vm_id_sub_in = int_and_i_vm_id;
assign vm_id_mul_in = int_and_i_vm_id;
assign vm_id_div_in = int_and_i_vm_id;
assign vm_id_rem_in = int_and_i_vm_id;

logic valid_i_add, ready_o_add, valid_o_add, ready_i_add;
logic valid_i_sub, ready_o_sub, valid_o_sub, ready_i_sub;
logic valid_i_mul, ready_o_mul, valid_o_mul, ready_i_mul;
logic valid_i_div, ready_o_div, valid_o_div, ready_i_div;
logic valid_i_rem, ready_o_rem, valid_o_rem, ready_i_rem;
wire [2:0]  integer_mode;
assign integer_mode = (int_and_isa[2:0] == 3'h3) ? 
                             (int_and_isa[5:3] == 3'h0) ? 3'b000 : // Add
                             (int_and_isa[5:3] == 3'h1) ? 3'b001 : // Subtract
                             (int_and_isa[5:3] == 3'h2) ? 3'b010 : // Multiply
                             (int_and_isa[5:3] == 3'h3) ? 3'b011 : // Divide
                             (int_and_isa[5:3] == 3'h4) ? 3'b100 : // Modulus
                             3'b000 : 3'b000; // Default to Add if conditions are not met
wire valid_i_main =  (integer_mode == 3'b000 || integer_mode == 3'b001 || integer_mode == 3'b010) ? (int_and_i_valid && !sync_full) : 0;
wire ready_i_main;
wire valid_o_main;
wire ready_o_main;
assign valid_i_div =   (integer_mode == 3'b011) ? (int_and_i_valid && !sync_full) : 0;
assign valid_i_rem =   (integer_mode == 3'b100) ? int_and_i_valid : 0;

//assign int_and_i_ready = (integer_mode == 3'b000) ? ready_o_add :
//                         (integer_mode == 3'b001) ? ready_o_sub :
//                         (integer_mode == 3'b010) ? ready_o_mul :
//                         (integer_mode == 3'b011) ? ready_o_div :
//                         (integer_mode == 3'b100) ? ready_o_rem : 0;
assign int_and_i_ready = ((valid_i_main && ready_o_main) ||
                          (valid_i_div && ready_o_div) ||
                          (valid_i_rem && ready_o_rem)) && !sync_full ;
                        

wire [FC_NUM-1:0]   sf = get_sf(int_and_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS]);
wire    [FC_NUM-1:0]   fc_dec = sf & {FC_NUM{int_and_o_valid & int_and_o_ready}};
wire    [3:0]   fc_dec_vm_id = int_and_o_vm_id;
/*
always @(posedge clk or negedge rstn)
if(!rstn) begin
     int_sq_fc_dec <= 2'b0;
     int_sq_fc_dec_vm_id <= 4'b0;
end else begin
     int_sq_fc_dec   <= fc_dec;
     int_sq_fc_dec_vm_id <= fc_dec_vm_id;
end
*/
always @* begin
     int_sq_fc_dec   = fc_dec;
     int_sq_fc_dec_vm_id = fc_dec_vm_id;
end

wire [ISA_BITS+REG_WIDTH+1-1:0] data_o_main;
   
// Instantiate the add128_signed_unsigned_pipeline module
js_int_alu u_main(
		  // Outputs
		  .ready_i		(ready_o_main),
		  .valid_o		(valid_o_main),
		  .data_o		(data_o_main[ISA_BITS+REG_WIDTH+1-1:0]),
		  .vm_id_o		(vm_id_o_main[3:0]),
		  // Inputs
		  .clk			(clk),
		  .rstn			(rstn),
		  .valid_i		(valid_i_main),
		  .vm_id_i		(int_and_i_vm_id[3:0]),
		  .data_i		(int_and_data[ISA_BITS+2*REG_WIDTH+1-1:0]),
		  .ready_o		(ready_i_main));

// Instantiate the div128_parallel_8bit module
divider div_inst (
     .clk(clk),
     .rst_n(rstn),
     .valid_i(valid_i_div),
     .ready_o(ready_o_div),
     .valid_o(valid_o_div),
     .ready_i(ready_i_div),
     .div_full_in(div_full_in),
     .div_full_out(div_full_out),
     .div_vm_id_in(vm_id_div_in),
     .div_vm_id_out(vm_id_div_out)
);

// Instantiate the rem128_parallel_8bit module
/*
remainder rem_inst (
     .clk(clk),
     .rst_n(rstn),
     .valid_i(valid_i_rem),
     .ready_o(ready_o_rem),
     .valid_o(valid_o_rem),
     .ready_i(ready_i_rem),
     .rem_full_in(rem_full_in),
     .rem_full_out(rem_full_out),
     .rem_vm_id_in(vm_id_rem_in),
     .rem_vm_id_out(vm_id_rem_out)
);
*/
assign ready_o_rem = 1'b1;
assign valid_o_rem = 1'b0;
assign rem_full_out = 'b0;
assign vm_id_rem_out = 4'b0;

//assign int_and_o_valid              = !sync_empty && (sync_dout ? valid_o_div : valid_o_main);
//assign int_and_o_vm_id              = !sync_empty ? sync_dout ? vm_id_div_out : vm_id_o_main : 4'h0;
//assign int_and_res                  = !sync_empty ? sync_dout ? div_full_out : data_o_main : 'b0;
//assign ready_i_div  = !sync_empty && sync_dout && int_and_o_ready;
//assign ready_i_main = !sync_empty && !sync_dout && int_and_o_ready;
wire                            merge_o_valid = !sync_empty && (sync_dout ? valid_o_div : valid_o_main);
wire [3:0]                      merge_o_vm_id = !sync_empty ? sync_dout ? vm_id_div_out : vm_id_o_main : 4'h0;
wire [ISA_BITS+REG_WIDTH+1-1:0] merge_o_res   = !sync_empty ? sync_dout ? div_full_out : data_o_main : 'b0;
wire                            merge_o_ready = !obuf_full;
assign ready_i_div  = !sync_empty && sync_dout && merge_o_ready;
assign ready_i_main = !sync_empty && !sync_dout && merge_o_ready;

assign ready_i_rem  = 1'b1;
reg  div_phase;
always @(posedge clk or negedge rstn)
if(!rstn)
     div_phase <= 1'b0;
else if(int_and_i_valid && integer_mode==3'b011 && !div_phase)
     div_phase <= 1'b1;
else if(valid_o_div && ready_i_div)
     div_phase <= 1'b0;

wire div_pulse = int_and_i_valid && integer_mode== 3'b011 && !div_phase;

assign sync_push = int_and_i_valid && (integer_mode==3'b011 ? div_pulse : int_and_i_ready);
assign sync_din = integer_mode==3'b011;


js_vm_sfifo #(.WIDTH(1), .DEPTH(4)) u_sync_fifo (
    .clk        (clk),
    .rstn       (rstn),
    .push       (sync_push),
    .din        (sync_din),
    .pop        (sync_pop),
    .dout       (sync_dout),
    .empty      (sync_empty),
    .full       (sync_full)
);

//assign sync_pop = int_and_o_valid && int_and_o_ready;
assign sync_pop = merge_o_valid && merge_o_ready;

assign    obuf_push = merge_o_valid && merge_o_ready;
assign    obuf_din  = {merge_o_vm_id, merge_o_res};
assign    int_and_o_valid = !obuf_empty;
assign    {int_and_o_vm_id, int_and_res} = obuf_dout;
assign    obuf_pop = int_and_o_valid && int_and_o_ready;

js_vm_sfifo #(.WIDTH(4+ISA_BITS+REG_WIDTH+1), .DEPTH(2)) u_out_fifo (
    .clk        (clk),
    .rstn       (rstn),
    .push       (obuf_push),
    .din        (obuf_din),
    .pop        (obuf_pop),
    .dout       (obuf_dout),
    .empty      (obuf_empty),
    .full       (obuf_full)
);

assign int_active = !obuf_empty || !sync_empty || int_and_i_valid;

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

