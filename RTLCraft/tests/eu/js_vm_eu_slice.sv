module js_vm_eu_slice (/*AUTOARG*/
   // Outputs
   slice_sq_pap_ready, slice_sq_map_ready, slice_sq_mip_ready,
   slice_sq_lgc_ready, slice_sq_alu_ready, slice_sq_tbt_ready,
   slice_sq_mov_ready, slice_pap_sq_fc_dec, slice_map_sq_fc_dec,
   slice_mip_sq_fc_dec, slice_lgc_sq_fc_dec, slice_alu_sq_fc_dec,
   slice_tbt_sq_fc_dec, slice_mov_sq_fc_dec,
   slice_pap_sq_hq_rel_valid, slice_cc_update, slice_cc_update_value,
   slice_rbank0_write_addr, slice_rbank0_write_data,
   slice_rbank0_write_valid, slice_rbank1_write_addr,
   slice_rbank1_write_data, slice_rbank1_write_valid,
   slice_eu_mh_valid, slice_eu_mh_index, slice_eu_mh_vm_id,
   slice_eu_mh_data, slice_eu_mh_type, slice_eu_mh_last,
   debug_mh_valid, debug_mh_data,
   // Inputs
   clk, rstn, aleo_cr_debug_mode, aleo_cr_debug_id, aleo_cr_q,
   aleo_cr_mu, slice_sq_pap_valid, slice_sq_pap_data,
   slice_sq_map_valid, slice_sq_map_data, slice_sq_mip_valid,
   slice_sq_mip_data, slice_sq_lgc_valid, slice_sq_lgc_data,
   slice_sq_alu_valid, slice_sq_alu_data, slice_sq_tbt_valid,
   slice_sq_tbt_data, slice_sq_mov_valid, slice_sq_mov_data,
   slice_eu_mh_ready, debug_mh_ready
   );

`include "js_vm.vh"
input               clk;
input               rstn;

input	[1:0]	aleo_cr_debug_mode;
input	[3:0]	aleo_cr_debug_id;

input	[255:0]	aleo_cr_q;
input	[255:0]	aleo_cr_mu;

input   [VM_PER_SLICE-1:0]							slice_sq_pap_valid;   // primary, mod mul
input   [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_sq_pap_data;
output  [VM_PER_SLICE-1:0]							slice_sq_pap_ready;

input   [VM_PER_SLICE-1:0]							slice_sq_map_valid;   // mod add
input   [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_sq_map_data;
output  [VM_PER_SLICE-1:0]        					slice_sq_map_ready;

input   [VM_PER_SLICE-1:0]        					slice_sq_mip_valid;   // mod inv
input   [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_sq_mip_data;
output  [VM_PER_SLICE-1:0]        					slice_sq_mip_ready;

input   [VM_PER_SLICE-1:0]        					slice_sq_lgc_valid;   // logic
input   [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_sq_lgc_data;
output  [VM_PER_SLICE-1:0]        					slice_sq_lgc_ready;

input   [VM_PER_SLICE-1:0]        					slice_sq_alu_valid;   // arithmetic
input   [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_sq_alu_data;
output  [VM_PER_SLICE-1:0]        					slice_sq_alu_ready;

input   [VM_PER_SLICE-1:0]        					slice_sq_tbt_valid;   // to-bits
input   [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_sq_tbt_data;
output  [VM_PER_SLICE-1:0]        					slice_sq_tbt_ready;

input   [VM_PER_SLICE-1:0]        					slice_sq_mov_valid;   // move
input   [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_sq_mov_data;
output  [VM_PER_SLICE-1:0]        					slice_sq_mov_ready;

output  [VM_PER_SLICE*FC_NUM-1:0]			slice_pap_sq_fc_dec;
output  [VM_PER_SLICE*FC_NUM-1:0]   		slice_map_sq_fc_dec;
output  [VM_PER_SLICE*FC_NUM-1:0]   		slice_mip_sq_fc_dec;
output  [VM_PER_SLICE*FC_NUM-1:0]   		slice_lgc_sq_fc_dec;
output  [VM_PER_SLICE*FC_NUM-1:0]   		slice_alu_sq_fc_dec;
output  [VM_PER_SLICE*FC_NUM-1:0]   		slice_tbt_sq_fc_dec;
output  [VM_PER_SLICE*FC_NUM-1:0]   		slice_mov_sq_fc_dec;

output  [VM_PER_SLICE-1:0]			slice_pap_sq_hq_rel_valid;


output logic	[VM_PER_SLICE-1:0] 					slice_cc_update;// From u_warb of js_vm_eu_warb.v
output logic	[VM_PER_SLICE-1:0] 					slice_cc_update_value;// From u_warb of js_vm_eu_warb.v
output logic	[VM_PER_SLICE*(GPR_ADDR_BITS-1)-1:0]slice_rbank0_write_addr;// From u_warb of js_vm_eu_warb.v
output logic	[VM_PER_SLICE*REG_WIDTH-1:0] 		slice_rbank0_write_data;// From u_warb of js_vm_eu_warb.v
output logic	[VM_PER_SLICE-1:0] 					slice_rbank0_write_valid;// From u_warb of js_vm_eu_warb.v
output logic	[VM_PER_SLICE*(GPR_ADDR_BITS-1)-1:0]slice_rbank1_write_addr;// From u_warb of js_vm_eu_warb.v
output logic	[VM_PER_SLICE*REG_WIDTH-1:0] 		slice_rbank1_write_data;// From u_warb of js_vm_eu_warb.v
output logic	[VM_PER_SLICE-1:0] 					slice_rbank1_write_valid;// From u_warb of js_vm_eu_warb.v


output logic    [VM_PER_SLICE-1:0]                  slice_eu_mh_valid;
output logic    [VM_PER_SLICE*18-1:0]               slice_eu_mh_index;
output logic    [VM_PER_SLICE*4-1:0]                slice_eu_mh_vm_id;
output logic    [VM_PER_SLICE*256-1:0]              slice_eu_mh_data;
output logic    [VM_PER_SLICE*4-1:0]                slice_eu_mh_type;
output logic    [VM_PER_SLICE-1:0]                  slice_eu_mh_last;
input  logic    [VM_PER_SLICE-1:0]                  slice_eu_mh_ready;

output				debug_mh_valid;
output	[255:0]		debug_mh_data;
input				debug_mh_ready;

localparam  ID_BITS = $clog2(VM_PER_SLICE);


/*AUTOINPUT*/



/*AUTOWIRE*/
wire [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_alu_sq_data;// From u_alu_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE-1:0]		slice_alu_sq_ready;	// From u_warb of js_vm_eu_warb.v
wire [VM_PER_SLICE-1:0]	slice_alu_sq_valid;	// From u_alu_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_lgc_sq_data;// From u_lgc_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE-1:0]		slice_lgc_sq_ready;	// From u_warb of js_vm_eu_warb.v
wire [VM_PER_SLICE-1:0]	slice_lgc_sq_valid;	// From u_lgc_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_map_sq_data;// From u_map_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE-1:0]		slice_map_sq_ready;	// From u_warb of js_vm_eu_warb.v
wire [VM_PER_SLICE-1:0]	slice_map_sq_valid;	// From u_map_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_mip_sq_data;// From u_mip_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE-1:0]		slice_mip_sq_ready;	// From u_warb of js_vm_eu_warb.v
wire [VM_PER_SLICE-1:0]	slice_mip_sq_valid;	// From u_mip_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_mov_sq_data;// From u_mov_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE-1:0]		slice_mov_sq_ready;	// From u_warb of js_vm_eu_warb.v
wire [VM_PER_SLICE-1:0]	slice_mov_sq_valid;	// From u_mov_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_pap_sq_data;// From u_pap_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE-1:0]		slice_pap_sq_ready;	// From u_warb of js_vm_eu_warb.v
wire [VM_PER_SLICE-1:0]	slice_pap_sq_valid;	// From u_pap_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_tbt_sq_data;// From u_tbt_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE*2-1:0] slice_tbt_sq_mask;	// From u_tbt_pipe of js_vm_eu_pipe.v
wire [VM_PER_SLICE-1:0]		slice_tbt_sq_ready;	// From u_warb of js_vm_eu_warb.v
wire [VM_PER_SLICE-1:0]	slice_tbt_sq_valid;	// From u_tbt_pipe of js_vm_eu_pipe.v


wire [4-1:0]	sq_alu_vm_id;		// From u_alu_iarb of js_vm_rr_arb.v
wire [4-1:0]	sq_lgc_vm_id;		// From u_lgc_iarb of js_vm_rr_arb.v
wire [4-1:0]	sq_map_vm_id;		// From u_map_iarb of js_vm_rr_arb.v
wire [4-1:0]	sq_mip_vm_id;		// From u_mip_iarb of js_vm_rr_arb.v
wire [4-1:0]	sq_mov_vm_id;		// From u_mov_iarb of js_vm_rr_arb.v
wire [4-1:0]	sq_pap_vm_id;		// From u_pap_iarb of js_vm_rr_arb.v
wire [4-1:0]	sq_tbt_vm_id;		// From u_tbt_iarb of js_vm_rr_arb.v

wire   logic         sq_pap_valid;
wire   logic [(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_pap_data;
wire                 sq_pap_ready;

wire   logic         sq_map_valid;
wire   logic [(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_map_data;
wire                 sq_map_ready;

wire   logic         sq_mip_valid;   // mod inv
wire   logic [(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_mip_data;
wire                 sq_mip_ready;

wire   logic         sq_lgc_valid;   // logic
wire   logic [(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_lgc_data;
wire                 sq_lgc_ready;

wire   logic         sq_alu_valid;   // arithmetic
wire   logic [(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_alu_data;
wire                 sq_alu_ready;

wire   logic         sq_tbt_valid;   // to-bits
wire   logic [(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_tbt_data;
wire                 sq_tbt_ready;

wire   logic         sq_mov_valid;   // move
wire   logic [(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_mov_data;
wire                 sq_mov_ready;

wire	[(ISA_BITS+2*REG_WIDTH+1)-1:0]	sq_pap_data_array	[0:VM_PER_SLICE-1];
wire	[(ISA_BITS+2*REG_WIDTH+1)-1:0]	sq_map_data_array	[0:VM_PER_SLICE-1];
wire	[(ISA_BITS+2*REG_WIDTH+1)-1:0]	sq_mip_data_array	[0:VM_PER_SLICE-1];
wire	[(ISA_BITS+2*REG_WIDTH+1)-1:0]	sq_lgc_data_array	[0:VM_PER_SLICE-1];
wire	[(ISA_BITS+2*REG_WIDTH+1)-1:0]	sq_alu_data_array	[0:VM_PER_SLICE-1];
wire	[(ISA_BITS+2*REG_WIDTH+1)-1:0]	sq_tbt_data_array	[0:VM_PER_SLICE-1];
wire	[(ISA_BITS+2*REG_WIDTH+1)-1:0]	sq_mov_data_array	[0:VM_PER_SLICE-1];

wire  logic [FC_NUM-1:0]	pap_sq_fc_dec;
wire  logic [3:0]	pap_sq_fc_dec_vm_id;
wire  logic [FC_NUM-1:0]	map_sq_fc_dec;	
wire  logic [3:0]	map_sq_fc_dec_vm_id;
wire  logic [FC_NUM-1:0]	mip_sq_fc_dec;
wire  logic [3:0]	mip_sq_fc_dec_vm_id;
wire  logic [FC_NUM-1:0]	lgc_sq_fc_dec;
wire  logic [3:0]	lgc_sq_fc_dec_vm_id;
wire  logic [FC_NUM-1:0]	alu_sq_fc_dec;
wire  logic [3:0]	alu_sq_fc_dec_vm_id;
wire  logic [FC_NUM-1:0]	tbt_sq_fc_dec;
wire  logic [3:0]	tbt_sq_fc_dec_vm_id;
wire  logic	[FC_NUM-1:0]	mov_sq_fc_dec;
wire  logic	[3:0]	mov_sq_fc_dec_vm_id;

wire  logic			pap_sq_hq_rel_valid;
wire  logic [3:0]	pap_sq_hq_rel_vm_id;


/*js_vm_eu_pipe AUTO_TEMPLATE "u_\(.*\)_pipe" (
	.slice_i_\(.*\)		(slice_sq_@_\1[]),
	.slice_o_\(.*\)		(slice_@_sq_\1[]),
	.slice_o_mask		(),
);
*/
js_vm_eu_pipe #(.PIPE_TYPE(0)) u_pap_pipe (/*AUTOINST*/
					   // Outputs
					   .slice_i_ready	(slice_sq_pap_ready[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_valid	(slice_pap_sq_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_data	(slice_pap_sq_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_mask	(),		 // Templated
					   .slice_o_fc_dec	(slice_pap_sq_fc_dec[VM_PER_SLICE*FC_NUM-1:0]), // Templated
					   .slice_o_hq_rel_valid(slice_pap_sq_hq_rel_valid[VM_PER_SLICE-1:0]), // Templated
					   // Inputs
					   .clk			(clk),
					   .rstn		(rstn),
					   .aleo_cr_q		(aleo_cr_q[255:0]),
					   .aleo_cr_mu		(aleo_cr_mu[255:0]),
					   .slice_i_valid	(slice_sq_pap_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_i_data	(slice_sq_pap_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_ready	(slice_pap_sq_ready[VM_PER_SLICE-1:0])); // Templated
/*js_vm_eu_pipe AUTO_TEMPLATE "u_\(.*\)_pipe" (
	.slice_i_\(.*\)		(slice_sq_@_\1[]),
	.slice_o_\(.*\)		(slice_@_sq_\1[]),
	.slice_o_mask		(),
	.slice_o_hq_rel_valid	(),
);
*/
js_vm_eu_pipe #(.PIPE_TYPE(1)) u_map_pipe (/*AUTOINST*/
					   // Outputs
					   .slice_i_ready	(slice_sq_map_ready[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_valid	(slice_map_sq_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_data	(slice_map_sq_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_mask	(),		 // Templated
					   .slice_o_fc_dec	(slice_map_sq_fc_dec[VM_PER_SLICE*FC_NUM-1:0]), // Templated
					   .slice_o_hq_rel_valid(),		 // Templated
					   // Inputs
					   .clk			(clk),
					   .rstn		(rstn),
					   .aleo_cr_q		(aleo_cr_q[255:0]),
					   .aleo_cr_mu		(aleo_cr_mu[255:0]),
					   .slice_i_valid	(slice_sq_map_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_i_data	(slice_sq_map_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_ready	(slice_map_sq_ready[VM_PER_SLICE-1:0])); // Templated
js_vm_eu_pipe #(.PIPE_TYPE(2)) u_mip_pipe (/*AUTOINST*/
					   // Outputs
					   .slice_i_ready	(slice_sq_mip_ready[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_valid	(slice_mip_sq_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_data	(slice_mip_sq_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_mask	(),		 // Templated
					   .slice_o_fc_dec	(slice_mip_sq_fc_dec[VM_PER_SLICE*FC_NUM-1:0]), // Templated
					   .slice_o_hq_rel_valid(),		 // Templated
					   // Inputs
					   .clk			(clk),
					   .rstn		(rstn),
					   .aleo_cr_q		(aleo_cr_q[255:0]),
					   .aleo_cr_mu		(aleo_cr_mu[255:0]),
					   .slice_i_valid	(slice_sq_mip_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_i_data	(slice_sq_mip_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_ready	(slice_mip_sq_ready[VM_PER_SLICE-1:0])); // Templated
js_vm_eu_pipe #(.PIPE_TYPE(3)) u_lgc_pipe (/*AUTOINST*/
					   // Outputs
					   .slice_i_ready	(slice_sq_lgc_ready[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_valid	(slice_lgc_sq_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_data	(slice_lgc_sq_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_mask	(),		 // Templated
					   .slice_o_fc_dec	(slice_lgc_sq_fc_dec[VM_PER_SLICE*FC_NUM-1:0]), // Templated
					   .slice_o_hq_rel_valid(),		 // Templated
					   // Inputs
					   .clk			(clk),
					   .rstn		(rstn),
					   .aleo_cr_q		(aleo_cr_q[255:0]),
					   .aleo_cr_mu		(aleo_cr_mu[255:0]),
					   .slice_i_valid	(slice_sq_lgc_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_i_data	(slice_sq_lgc_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_ready	(slice_lgc_sq_ready[VM_PER_SLICE-1:0])); // Templated
js_vm_eu_pipe #(.PIPE_TYPE(4)) u_alu_pipe (/*AUTOINST*/
					   // Outputs
					   .slice_i_ready	(slice_sq_alu_ready[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_valid	(slice_alu_sq_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_data	(slice_alu_sq_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_mask	(),		 // Templated
					   .slice_o_fc_dec	(slice_alu_sq_fc_dec[VM_PER_SLICE*FC_NUM-1:0]), // Templated
					   .slice_o_hq_rel_valid(),		 // Templated
					   // Inputs
					   .clk			(clk),
					   .rstn		(rstn),
					   .aleo_cr_q		(aleo_cr_q[255:0]),
					   .aleo_cr_mu		(aleo_cr_mu[255:0]),
					   .slice_i_valid	(slice_sq_alu_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_i_data	(slice_sq_alu_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_ready	(slice_alu_sq_ready[VM_PER_SLICE-1:0])); // Templated
js_vm_eu_pipe #(.PIPE_TYPE(6)) u_mov_pipe (/*AUTOINST*/
					   // Outputs
					   .slice_i_ready	(slice_sq_mov_ready[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_valid	(slice_mov_sq_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_data	(slice_mov_sq_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_mask	(),		 // Templated
					   .slice_o_fc_dec	(slice_mov_sq_fc_dec[VM_PER_SLICE*FC_NUM-1:0]), // Templated
					   .slice_o_hq_rel_valid(),		 // Templated
					   // Inputs
					   .clk			(clk),
					   .rstn		(rstn),
					   .aleo_cr_q		(aleo_cr_q[255:0]),
					   .aleo_cr_mu		(aleo_cr_mu[255:0]),
					   .slice_i_valid	(slice_sq_mov_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_i_data	(slice_sq_mov_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_ready	(slice_mov_sq_ready[VM_PER_SLICE-1:0])); // Templated

/*js_vm_eu_pipe AUTO_TEMPLATE "u_\(.*\)_pipe" (
	.slice_i_\(.*\)		(slice_sq_@_\1[]),
	.slice_o_\(.*\)		(slice_@_sq_\1[]),
	.slice_o_hq_rel_valid	(),
);
*/
js_vm_eu_pipe #(.PIPE_TYPE(5)) u_tbt_pipe (/*AUTOINST*/
					   // Outputs
					   .slice_i_ready	(slice_sq_tbt_ready[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_valid	(slice_tbt_sq_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_o_data	(slice_tbt_sq_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_mask	(slice_tbt_sq_mask[VM_PER_SLICE*2-1:0]), // Templated
					   .slice_o_fc_dec	(slice_tbt_sq_fc_dec[VM_PER_SLICE*FC_NUM-1:0]), // Templated
					   .slice_o_hq_rel_valid(),		 // Templated
					   // Inputs
					   .clk			(clk),
					   .rstn		(rstn),
					   .aleo_cr_q		(aleo_cr_q[255:0]),
					   .aleo_cr_mu		(aleo_cr_mu[255:0]),
					   .slice_i_valid	(slice_sq_tbt_valid[VM_PER_SLICE-1:0]), // Templated
					   .slice_i_data	(slice_sq_tbt_data[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]), // Templated
					   .slice_o_ready	(slice_tbt_sq_ready[VM_PER_SLICE-1:0])); // Templated

wire	[VM_PER_SLICE-1:0]	slice_debug_mh_valid;
logic	[VM_PER_SLICE-1:0]	slice_debug_mh_ready;
wire	[255:0]				slice_debug_mh_data		[VM_PER_SLICE-1:0];
assign	debug_mh_valid 	= slice_debug_mh_valid[aleo_cr_debug_id[1:0]] && aleo_cr_debug_mode[1];
assign	debug_mh_data	= slice_debug_mh_data[aleo_cr_debug_id[1:0]];

generate
	if(VM_PER_SLICE==1) begin
		always @* begin
			slice_debug_mh_ready = debug_mh_ready;
		end
	end else begin
		always @* begin
			slice_debug_mh_ready =  {VM_PER_SLICE{1'b1}};
			slice_debug_mh_ready[aleo_cr_debug_id[1:0]] = debug_mh_ready;
		end
	end
endgenerate
/*js_vm_eu_warb AUTO_TEMPLATE (
	.\(.*\)_sq_valid	(slice_\1_sq_valid[i]),
	.\(.*\)_sq_ready	(slice_\1_sq_ready[i]),
	.\(.*\)_sq_res		(slice_\1_sq_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]),
	.mac_sq_valid		(slice_tbt_sq_valid[i]),
	.mac_sq_ready		(slice_tbt_sq_ready[i]),
	.mac_sq_res		(slice_tbt_sq_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]),
	.mac_sq_mask		(slice_tbt_sq_mask[i*2+:2]),
	.cc_update			(slice_cc_update[i]),
	.cc_update_value	(slice_cc_update_value[i]),
	.rbank0_write_valid	(slice_rbank0_write_valid[i]),
	.rbank1_write_valid	(slice_rbank1_write_valid[i]),
	.rbank0_write_addr	(slice_rbank0_write_addr[i*(GPR_ADDR_BITS-1)+:(GPR_ADDR_BITS-1)]),
	.rbank1_write_addr	(slice_rbank1_write_addr[i*(GPR_ADDR_BITS-1)+:(GPR_ADDR_BITS-1)]),
	.rbank0_write_data	(slice_rbank0_write_data[i*(REG_WIDTH)+:(REG_WIDTH)]),
	.rbank1_write_data	(slice_rbank1_write_data[i*(REG_WIDTH)+:(REG_WIDTH)]),
	.eu_mh_valid	(slice_eu_mh_valid[i]),
	.eu_mh_ready	(slice_eu_mh_ready[i]),
	.eu_mh_vm_id	(),
	.eu_mh_index	(slice_eu_mh_index[i*18+:18]),
	.eu_mh_data		(slice_eu_mh_data[i*256+:256]),
	.eu_mh_type		(slice_eu_mh_type[i*4+:4]),
	.eu_mh_last		(slice_eu_mh_last[i]),
	.debug_mh_valid	(slice_debug_mh_valid[i]),
	.debug_mh_data	(slice_debug_mh_data[i][]),
	.debug_mh_ready	(slice_debug_mh_ready[i]),

);
*/
genvar i;
generate
	for(i=0; i<VM_PER_SLICE; i=i+1) begin
js_vm_eu_warb u_warb (/*AUTOINST*/
		      // Outputs
		      .pap_sq_ready	(slice_pap_sq_ready[i]), // Templated
		      .lgc_sq_ready	(slice_lgc_sq_ready[i]), // Templated
		      .map_sq_ready	(slice_map_sq_ready[i]), // Templated
		      .mac_sq_ready	(slice_tbt_sq_ready[i]), // Templated
		      .alu_sq_ready	(slice_alu_sq_ready[i]), // Templated
		      .mip_sq_ready	(slice_mip_sq_ready[i]), // Templated
		      .mov_sq_ready	(slice_mov_sq_ready[i]), // Templated
		      .cc_update	(slice_cc_update[i]),	 // Templated
		      .cc_update_value	(slice_cc_update_value[i]), // Templated
		      .rbank0_write_addr(slice_rbank0_write_addr[i*(GPR_ADDR_BITS-1)+:(GPR_ADDR_BITS-1)]), // Templated
		      .rbank0_write_data(slice_rbank0_write_data[i*(REG_WIDTH)+:(REG_WIDTH)]), // Templated
		      .rbank0_write_valid(slice_rbank0_write_valid[i]), // Templated
		      .rbank1_write_addr(slice_rbank1_write_addr[i*(GPR_ADDR_BITS-1)+:(GPR_ADDR_BITS-1)]), // Templated
		      .rbank1_write_data(slice_rbank1_write_data[i*(REG_WIDTH)+:(REG_WIDTH)]), // Templated
		      .rbank1_write_valid(slice_rbank1_write_valid[i]), // Templated
		      .eu_mh_valid	(slice_eu_mh_valid[i]),	 // Templated
		      .eu_mh_index	(slice_eu_mh_index[i*18+:18]), // Templated
		      .eu_mh_vm_id	(),			 // Templated
		      .eu_mh_data	(slice_eu_mh_data[i*256+:256]), // Templated
		      .eu_mh_type	(slice_eu_mh_type[i*4+:4]), // Templated
		      .eu_mh_last	(slice_eu_mh_last[i]),	 // Templated
		      .debug_mh_valid	(slice_debug_mh_valid[i]), // Templated
		      .debug_mh_data	(slice_debug_mh_data[i][255:0]), // Templated
		      // Inputs
		      .clk		(clk),
		      .rstn		(rstn),
		      .aleo_cr_debug_id	(aleo_cr_debug_id[3:0]),
		      .aleo_cr_debug_mode(aleo_cr_debug_mode[1:0]),
		      .pap_sq_valid	(slice_pap_sq_valid[i]), // Templated
		      .pap_sq_res	(slice_pap_sq_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]), // Templated
		      .lgc_sq_valid	(slice_lgc_sq_valid[i]), // Templated
		      .lgc_sq_res	(slice_lgc_sq_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]), // Templated
		      .map_sq_valid	(slice_map_sq_valid[i]), // Templated
		      .map_sq_res	(slice_map_sq_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]), // Templated
		      .mac_sq_valid	(slice_tbt_sq_valid[i]), // Templated
		      .mac_sq_mask	(slice_tbt_sq_mask[i*2+:2]), // Templated
		      .mac_sq_res	(slice_tbt_sq_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]), // Templated
		      .alu_sq_valid	(slice_alu_sq_valid[i]), // Templated
		      .alu_sq_res	(slice_alu_sq_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]), // Templated
		      .mip_sq_valid	(slice_mip_sq_valid[i]), // Templated
		      .mip_sq_res	(slice_mip_sq_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]), // Templated
		      .mov_sq_valid	(slice_mov_sq_valid[i]), // Templated
		      .mov_sq_res	(slice_mov_sq_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]), // Templated
		      .eu_mh_ready	(slice_eu_mh_ready[i]),	 // Templated
		      .debug_mh_ready	(slice_debug_mh_ready[i])); // Templated
	end

endgenerate
endmodule
// Verilog-mode Setting:
// Local Variables:
// verilog-library-directories: ("../sq/" "../regfile/" "./" "../eu/bits/" "../eu/integer/" "../eu/mod/" "../eu/macro" "../eu/mod/inv" "../eu/mod/mul" "../eu" "../new")
// verilog-auto-inst-param-value: t
// End:

