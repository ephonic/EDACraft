module js_vm_eu (/*AUTOARG*/
   // Outputs
   sq_pap_readys, sq_map_readys, sq_mip_readys, sq_lgc_readys,
   sq_alu_readys, sq_tbt_readys, sq_mov_readys, pap_sq_fc_dec,
   map_sq_fc_dec, mip_sq_fc_dec, lgc_sq_fc_dec, alu_sq_fc_dec,
   tbt_sq_fc_dec, mov_sq_fc_dec, pap_sq_hq_rel_valid, debug_mh_data,
   debug_mh_valid, vm0_cc_update, vm0_cc_update_value, vm0_eu_mh_data,
   vm0_eu_mh_index, vm0_eu_mh_last, vm0_eu_mh_type, vm0_eu_mh_valid,
   vm0_rbank0_write_addr, vm0_rbank0_write_data,
   vm0_rbank0_write_valid, vm0_rbank1_write_addr,
   vm0_rbank1_write_data, vm0_rbank1_write_valid, vm10_cc_update,
   vm10_cc_update_value, vm10_eu_mh_data, vm10_eu_mh_index,
   vm10_eu_mh_last, vm10_eu_mh_type, vm10_eu_mh_valid,
   vm10_rbank0_write_addr, vm10_rbank0_write_data,
   vm10_rbank0_write_valid, vm10_rbank1_write_addr,
   vm10_rbank1_write_data, vm10_rbank1_write_valid, vm11_cc_update,
   vm11_cc_update_value, vm11_eu_mh_data, vm11_eu_mh_index,
   vm11_eu_mh_last, vm11_eu_mh_type, vm11_eu_mh_valid,
   vm11_rbank0_write_addr, vm11_rbank0_write_data,
   vm11_rbank0_write_valid, vm11_rbank1_write_addr,
   vm11_rbank1_write_data, vm11_rbank1_write_valid, vm12_cc_update,
   vm12_cc_update_value, vm12_eu_mh_data, vm12_eu_mh_index,
   vm12_eu_mh_last, vm12_eu_mh_type, vm12_eu_mh_valid,
   vm12_rbank0_write_addr, vm12_rbank0_write_data,
   vm12_rbank0_write_valid, vm12_rbank1_write_addr,
   vm12_rbank1_write_data, vm12_rbank1_write_valid, vm13_cc_update,
   vm13_cc_update_value, vm13_eu_mh_data, vm13_eu_mh_index,
   vm13_eu_mh_last, vm13_eu_mh_type, vm13_eu_mh_valid,
   vm13_rbank0_write_addr, vm13_rbank0_write_data,
   vm13_rbank0_write_valid, vm13_rbank1_write_addr,
   vm13_rbank1_write_data, vm13_rbank1_write_valid, vm14_cc_update,
   vm14_cc_update_value, vm14_eu_mh_data, vm14_eu_mh_index,
   vm14_eu_mh_last, vm14_eu_mh_type, vm14_eu_mh_valid,
   vm14_rbank0_write_addr, vm14_rbank0_write_data,
   vm14_rbank0_write_valid, vm14_rbank1_write_addr,
   vm14_rbank1_write_data, vm14_rbank1_write_valid, vm15_cc_update,
   vm15_cc_update_value, vm15_eu_mh_data, vm15_eu_mh_index,
   vm15_eu_mh_last, vm15_eu_mh_type, vm15_eu_mh_valid,
   vm15_rbank0_write_addr, vm15_rbank0_write_data,
   vm15_rbank0_write_valid, vm15_rbank1_write_addr,
   vm15_rbank1_write_data, vm15_rbank1_write_valid, vm1_cc_update,
   vm1_cc_update_value, vm1_eu_mh_data, vm1_eu_mh_index,
   vm1_eu_mh_last, vm1_eu_mh_type, vm1_eu_mh_valid,
   vm1_rbank0_write_addr, vm1_rbank0_write_data,
   vm1_rbank0_write_valid, vm1_rbank1_write_addr,
   vm1_rbank1_write_data, vm1_rbank1_write_valid, vm2_cc_update,
   vm2_cc_update_value, vm2_eu_mh_data, vm2_eu_mh_index,
   vm2_eu_mh_last, vm2_eu_mh_type, vm2_eu_mh_valid,
   vm2_rbank0_write_addr, vm2_rbank0_write_data,
   vm2_rbank0_write_valid, vm2_rbank1_write_addr,
   vm2_rbank1_write_data, vm2_rbank1_write_valid, vm3_cc_update,
   vm3_cc_update_value, vm3_eu_mh_data, vm3_eu_mh_index,
   vm3_eu_mh_last, vm3_eu_mh_type, vm3_eu_mh_valid,
   vm3_rbank0_write_addr, vm3_rbank0_write_data,
   vm3_rbank0_write_valid, vm3_rbank1_write_addr,
   vm3_rbank1_write_data, vm3_rbank1_write_valid, vm4_cc_update,
   vm4_cc_update_value, vm4_eu_mh_data, vm4_eu_mh_index,
   vm4_eu_mh_last, vm4_eu_mh_type, vm4_eu_mh_valid,
   vm4_rbank0_write_addr, vm4_rbank0_write_data,
   vm4_rbank0_write_valid, vm4_rbank1_write_addr,
   vm4_rbank1_write_data, vm4_rbank1_write_valid, vm5_cc_update,
   vm5_cc_update_value, vm5_eu_mh_data, vm5_eu_mh_index,
   vm5_eu_mh_last, vm5_eu_mh_type, vm5_eu_mh_valid,
   vm5_rbank0_write_addr, vm5_rbank0_write_data,
   vm5_rbank0_write_valid, vm5_rbank1_write_addr,
   vm5_rbank1_write_data, vm5_rbank1_write_valid, vm6_cc_update,
   vm6_cc_update_value, vm6_eu_mh_data, vm6_eu_mh_index,
   vm6_eu_mh_last, vm6_eu_mh_type, vm6_eu_mh_valid,
   vm6_rbank0_write_addr, vm6_rbank0_write_data,
   vm6_rbank0_write_valid, vm6_rbank1_write_addr,
   vm6_rbank1_write_data, vm6_rbank1_write_valid, vm7_cc_update,
   vm7_cc_update_value, vm7_eu_mh_data, vm7_eu_mh_index,
   vm7_eu_mh_last, vm7_eu_mh_type, vm7_eu_mh_valid,
   vm7_rbank0_write_addr, vm7_rbank0_write_data,
   vm7_rbank0_write_valid, vm7_rbank1_write_addr,
   vm7_rbank1_write_data, vm7_rbank1_write_valid, vm8_cc_update,
   vm8_cc_update_value, vm8_eu_mh_data, vm8_eu_mh_index,
   vm8_eu_mh_last, vm8_eu_mh_type, vm8_eu_mh_valid,
   vm8_rbank0_write_addr, vm8_rbank0_write_data,
   vm8_rbank0_write_valid, vm8_rbank1_write_addr,
   vm8_rbank1_write_data, vm8_rbank1_write_valid, vm9_cc_update,
   vm9_cc_update_value, vm9_eu_mh_data, vm9_eu_mh_index,
   vm9_eu_mh_last, vm9_eu_mh_type, vm9_eu_mh_valid,
   vm9_rbank0_write_addr, vm9_rbank0_write_data,
   vm9_rbank0_write_valid, vm9_rbank1_write_addr,
   vm9_rbank1_write_data, vm9_rbank1_write_valid,
   // Inputs
   clk, rstn, aleo_cr_debug_mode, aleo_cr_debug_id, aleo_cr_q,
   aleo_cr_mu, sq_pap_valids, sq_pap_datas, sq_map_valids,
   sq_map_datas, sq_mip_valids, sq_mip_datas, sq_lgc_valids,
   sq_lgc_datas, sq_alu_valids, sq_alu_datas, sq_tbt_valids,
   sq_tbt_datas, sq_mov_valids, sq_mov_datas, debug_mh_ready,
   vm0_eu_mh_ready, vm1_eu_mh_ready, vm2_eu_mh_ready, vm3_eu_mh_ready,
   vm4_eu_mh_ready, vm5_eu_mh_ready, vm6_eu_mh_ready, vm7_eu_mh_ready,
   vm8_eu_mh_ready, vm9_eu_mh_ready, vm10_eu_mh_ready,
   vm11_eu_mh_ready, vm12_eu_mh_ready, vm13_eu_mh_ready,
   vm14_eu_mh_ready, vm15_eu_mh_ready
   );
`include "js_vm.vh"
input               clk;
input               rstn;

input	[1:0]	aleo_cr_debug_mode;
input	[3:0]	aleo_cr_debug_id;

input	[255:0]	aleo_cr_q;
input	[255:0]	aleo_cr_mu;

input   logic [15:0]        sq_pap_valids;
input   logic [16*(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_pap_datas;
output        [15:0]        sq_pap_readys;

input   logic [15:0]        sq_map_valids;
input   logic [16*(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_map_datas;
output        [15:0]        sq_map_readys;

input   logic [15:0]        sq_mip_valids;   // mod inv
input   logic [16*(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_mip_datas;
output        [15:0]        sq_mip_readys;

input   logic [15:0]        sq_lgc_valids;   // logic
input   logic [16*(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_lgc_datas;
output        [15:0]        sq_lgc_readys;

input   logic [15:0]        sq_alu_valids;   // arithmetic
input   logic [16*(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_alu_datas;
output        [15:0]        sq_alu_readys;

input   logic [15:0]        sq_tbt_valids;   // to-bits
input   logic [16*(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_tbt_datas;
output        [15:0]        sq_tbt_readys;

input   logic [15:0]        sq_mov_valids;   // move
input   logic [16*(ISA_BITS+2*REG_WIDTH+1)-1:0] sq_mov_datas;
output        [15:0]        sq_mov_readys;

output  [16*FC_NUM-1:0]   pap_sq_fc_dec;
output  [16*FC_NUM-1:0]   map_sq_fc_dec;
output  [16*FC_NUM-1:0]   mip_sq_fc_dec;
output  [16*FC_NUM-1:0]   lgc_sq_fc_dec;
output  [16*FC_NUM-1:0]   alu_sq_fc_dec;
output  [16*FC_NUM-1:0]   tbt_sq_fc_dec;
output  [16*FC_NUM-1:0]   mov_sq_fc_dec;


output  [15:0]  pap_sq_hq_rel_valid;


output [255:0]		debug_mh_data;		// From u_vm0_slice of js_vm_eu_slice.v
output			debug_mh_valid;		// From u_vm0_slice of js_vm_eu_slice.v
output			vm0_cc_update;		// From u_vm0_slice of js_vm_eu_slice.v
output			vm0_cc_update_value;	// From u_vm0_slice of js_vm_eu_slice.v
output [255:0]		vm0_eu_mh_data;		// From u_vm0_slice of js_vm_eu_slice.v
output [17:0]		vm0_eu_mh_index;	// From u_vm0_slice of js_vm_eu_slice.v
output			vm0_eu_mh_last;		// From u_vm0_slice of js_vm_eu_slice.v
output [3:0]		vm0_eu_mh_type;		// From u_vm0_slice of js_vm_eu_slice.v
output			vm0_eu_mh_valid;	// From u_vm0_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm0_rbank0_write_addr;// From u_vm0_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm0_rbank0_write_data;	// From u_vm0_slice of js_vm_eu_slice.v
output			vm0_rbank0_write_valid;	// From u_vm0_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm0_rbank1_write_addr;// From u_vm0_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm0_rbank1_write_data;	// From u_vm0_slice of js_vm_eu_slice.v
output			vm0_rbank1_write_valid;	// From u_vm0_slice of js_vm_eu_slice.v
output			vm10_cc_update;		// From u_vm10_slice of js_vm_eu_slice.v
output			vm10_cc_update_value;	// From u_vm10_slice of js_vm_eu_slice.v
output [255:0]		vm10_eu_mh_data;	// From u_vm10_slice of js_vm_eu_slice.v
output [17:0]		vm10_eu_mh_index;	// From u_vm10_slice of js_vm_eu_slice.v
output			vm10_eu_mh_last;	// From u_vm10_slice of js_vm_eu_slice.v
output [3:0]		vm10_eu_mh_type;	// From u_vm10_slice of js_vm_eu_slice.v
output			vm10_eu_mh_valid;	// From u_vm10_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm10_rbank0_write_addr;// From u_vm10_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm10_rbank0_write_data;	// From u_vm10_slice of js_vm_eu_slice.v
output			vm10_rbank0_write_valid;// From u_vm10_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm10_rbank1_write_addr;// From u_vm10_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm10_rbank1_write_data;	// From u_vm10_slice of js_vm_eu_slice.v
output			vm10_rbank1_write_valid;// From u_vm10_slice of js_vm_eu_slice.v
output			vm11_cc_update;		// From u_vm11_slice of js_vm_eu_slice.v
output			vm11_cc_update_value;	// From u_vm11_slice of js_vm_eu_slice.v
output [255:0]		vm11_eu_mh_data;	// From u_vm11_slice of js_vm_eu_slice.v
output [17:0]		vm11_eu_mh_index;	// From u_vm11_slice of js_vm_eu_slice.v
output			vm11_eu_mh_last;	// From u_vm11_slice of js_vm_eu_slice.v
output [3:0]		vm11_eu_mh_type;	// From u_vm11_slice of js_vm_eu_slice.v
output			vm11_eu_mh_valid;	// From u_vm11_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm11_rbank0_write_addr;// From u_vm11_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm11_rbank0_write_data;	// From u_vm11_slice of js_vm_eu_slice.v
output			vm11_rbank0_write_valid;// From u_vm11_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm11_rbank1_write_addr;// From u_vm11_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm11_rbank1_write_data;	// From u_vm11_slice of js_vm_eu_slice.v
output			vm11_rbank1_write_valid;// From u_vm11_slice of js_vm_eu_slice.v
output			vm12_cc_update;		// From u_vm12_slice of js_vm_eu_slice.v
output			vm12_cc_update_value;	// From u_vm12_slice of js_vm_eu_slice.v
output [255:0]		vm12_eu_mh_data;	// From u_vm12_slice of js_vm_eu_slice.v
output [17:0]		vm12_eu_mh_index;	// From u_vm12_slice of js_vm_eu_slice.v
output			vm12_eu_mh_last;	// From u_vm12_slice of js_vm_eu_slice.v
output [3:0]		vm12_eu_mh_type;	// From u_vm12_slice of js_vm_eu_slice.v
output			vm12_eu_mh_valid;	// From u_vm12_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm12_rbank0_write_addr;// From u_vm12_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm12_rbank0_write_data;	// From u_vm12_slice of js_vm_eu_slice.v
output			vm12_rbank0_write_valid;// From u_vm12_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm12_rbank1_write_addr;// From u_vm12_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm12_rbank1_write_data;	// From u_vm12_slice of js_vm_eu_slice.v
output			vm12_rbank1_write_valid;// From u_vm12_slice of js_vm_eu_slice.v
output			vm13_cc_update;		// From u_vm13_slice of js_vm_eu_slice.v
output			vm13_cc_update_value;	// From u_vm13_slice of js_vm_eu_slice.v
output [255:0]		vm13_eu_mh_data;	// From u_vm13_slice of js_vm_eu_slice.v
output [17:0]		vm13_eu_mh_index;	// From u_vm13_slice of js_vm_eu_slice.v
output			vm13_eu_mh_last;	// From u_vm13_slice of js_vm_eu_slice.v
output [3:0]		vm13_eu_mh_type;	// From u_vm13_slice of js_vm_eu_slice.v
output			vm13_eu_mh_valid;	// From u_vm13_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm13_rbank0_write_addr;// From u_vm13_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm13_rbank0_write_data;	// From u_vm13_slice of js_vm_eu_slice.v
output			vm13_rbank0_write_valid;// From u_vm13_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm13_rbank1_write_addr;// From u_vm13_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm13_rbank1_write_data;	// From u_vm13_slice of js_vm_eu_slice.v
output			vm13_rbank1_write_valid;// From u_vm13_slice of js_vm_eu_slice.v
output			vm14_cc_update;		// From u_vm14_slice of js_vm_eu_slice.v
output			vm14_cc_update_value;	// From u_vm14_slice of js_vm_eu_slice.v
output [255:0]		vm14_eu_mh_data;	// From u_vm14_slice of js_vm_eu_slice.v
output [17:0]		vm14_eu_mh_index;	// From u_vm14_slice of js_vm_eu_slice.v
output			vm14_eu_mh_last;	// From u_vm14_slice of js_vm_eu_slice.v
output [3:0]		vm14_eu_mh_type;	// From u_vm14_slice of js_vm_eu_slice.v
output			vm14_eu_mh_valid;	// From u_vm14_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm14_rbank0_write_addr;// From u_vm14_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm14_rbank0_write_data;	// From u_vm14_slice of js_vm_eu_slice.v
output			vm14_rbank0_write_valid;// From u_vm14_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm14_rbank1_write_addr;// From u_vm14_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm14_rbank1_write_data;	// From u_vm14_slice of js_vm_eu_slice.v
output			vm14_rbank1_write_valid;// From u_vm14_slice of js_vm_eu_slice.v
output			vm15_cc_update;		// From u_vm15_slice of js_vm_eu_slice.v
output			vm15_cc_update_value;	// From u_vm15_slice of js_vm_eu_slice.v
output [255:0]		vm15_eu_mh_data;	// From u_vm15_slice of js_vm_eu_slice.v
output [17:0]		vm15_eu_mh_index;	// From u_vm15_slice of js_vm_eu_slice.v
output			vm15_eu_mh_last;	// From u_vm15_slice of js_vm_eu_slice.v
output [3:0]		vm15_eu_mh_type;	// From u_vm15_slice of js_vm_eu_slice.v
output			vm15_eu_mh_valid;	// From u_vm15_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm15_rbank0_write_addr;// From u_vm15_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm15_rbank0_write_data;	// From u_vm15_slice of js_vm_eu_slice.v
output			vm15_rbank0_write_valid;// From u_vm15_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm15_rbank1_write_addr;// From u_vm15_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm15_rbank1_write_data;	// From u_vm15_slice of js_vm_eu_slice.v
output			vm15_rbank1_write_valid;// From u_vm15_slice of js_vm_eu_slice.v
output			vm1_cc_update;		// From u_vm1_slice of js_vm_eu_slice.v
output			vm1_cc_update_value;	// From u_vm1_slice of js_vm_eu_slice.v
output [255:0]		vm1_eu_mh_data;		// From u_vm1_slice of js_vm_eu_slice.v
output [17:0]		vm1_eu_mh_index;	// From u_vm1_slice of js_vm_eu_slice.v
output			vm1_eu_mh_last;		// From u_vm1_slice of js_vm_eu_slice.v
output [3:0]		vm1_eu_mh_type;		// From u_vm1_slice of js_vm_eu_slice.v
output			vm1_eu_mh_valid;	// From u_vm1_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm1_rbank0_write_addr;// From u_vm1_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm1_rbank0_write_data;	// From u_vm1_slice of js_vm_eu_slice.v
output			vm1_rbank0_write_valid;	// From u_vm1_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm1_rbank1_write_addr;// From u_vm1_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm1_rbank1_write_data;	// From u_vm1_slice of js_vm_eu_slice.v
output			vm1_rbank1_write_valid;	// From u_vm1_slice of js_vm_eu_slice.v
output			vm2_cc_update;		// From u_vm2_slice of js_vm_eu_slice.v
output			vm2_cc_update_value;	// From u_vm2_slice of js_vm_eu_slice.v
output [255:0]		vm2_eu_mh_data;		// From u_vm2_slice of js_vm_eu_slice.v
output [17:0]		vm2_eu_mh_index;	// From u_vm2_slice of js_vm_eu_slice.v
output			vm2_eu_mh_last;		// From u_vm2_slice of js_vm_eu_slice.v
output [3:0]		vm2_eu_mh_type;		// From u_vm2_slice of js_vm_eu_slice.v
output			vm2_eu_mh_valid;	// From u_vm2_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm2_rbank0_write_addr;// From u_vm2_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm2_rbank0_write_data;	// From u_vm2_slice of js_vm_eu_slice.v
output			vm2_rbank0_write_valid;	// From u_vm2_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm2_rbank1_write_addr;// From u_vm2_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm2_rbank1_write_data;	// From u_vm2_slice of js_vm_eu_slice.v
output			vm2_rbank1_write_valid;	// From u_vm2_slice of js_vm_eu_slice.v
output			vm3_cc_update;		// From u_vm3_slice of js_vm_eu_slice.v
output			vm3_cc_update_value;	// From u_vm3_slice of js_vm_eu_slice.v
output [255:0]		vm3_eu_mh_data;		// From u_vm3_slice of js_vm_eu_slice.v
output [17:0]		vm3_eu_mh_index;	// From u_vm3_slice of js_vm_eu_slice.v
output			vm3_eu_mh_last;		// From u_vm3_slice of js_vm_eu_slice.v
output [3:0]		vm3_eu_mh_type;		// From u_vm3_slice of js_vm_eu_slice.v
output			vm3_eu_mh_valid;	// From u_vm3_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm3_rbank0_write_addr;// From u_vm3_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm3_rbank0_write_data;	// From u_vm3_slice of js_vm_eu_slice.v
output			vm3_rbank0_write_valid;	// From u_vm3_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm3_rbank1_write_addr;// From u_vm3_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm3_rbank1_write_data;	// From u_vm3_slice of js_vm_eu_slice.v
output			vm3_rbank1_write_valid;	// From u_vm3_slice of js_vm_eu_slice.v
output			vm4_cc_update;		// From u_vm4_slice of js_vm_eu_slice.v
output			vm4_cc_update_value;	// From u_vm4_slice of js_vm_eu_slice.v
output [255:0]		vm4_eu_mh_data;		// From u_vm4_slice of js_vm_eu_slice.v
output [17:0]		vm4_eu_mh_index;	// From u_vm4_slice of js_vm_eu_slice.v
output			vm4_eu_mh_last;		// From u_vm4_slice of js_vm_eu_slice.v
output [3:0]		vm4_eu_mh_type;		// From u_vm4_slice of js_vm_eu_slice.v
output			vm4_eu_mh_valid;	// From u_vm4_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm4_rbank0_write_addr;// From u_vm4_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm4_rbank0_write_data;	// From u_vm4_slice of js_vm_eu_slice.v
output			vm4_rbank0_write_valid;	// From u_vm4_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm4_rbank1_write_addr;// From u_vm4_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm4_rbank1_write_data;	// From u_vm4_slice of js_vm_eu_slice.v
output			vm4_rbank1_write_valid;	// From u_vm4_slice of js_vm_eu_slice.v
output			vm5_cc_update;		// From u_vm5_slice of js_vm_eu_slice.v
output			vm5_cc_update_value;	// From u_vm5_slice of js_vm_eu_slice.v
output [255:0]		vm5_eu_mh_data;		// From u_vm5_slice of js_vm_eu_slice.v
output [17:0]		vm5_eu_mh_index;	// From u_vm5_slice of js_vm_eu_slice.v
output			vm5_eu_mh_last;		// From u_vm5_slice of js_vm_eu_slice.v
output [3:0]		vm5_eu_mh_type;		// From u_vm5_slice of js_vm_eu_slice.v
output			vm5_eu_mh_valid;	// From u_vm5_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm5_rbank0_write_addr;// From u_vm5_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm5_rbank0_write_data;	// From u_vm5_slice of js_vm_eu_slice.v
output			vm5_rbank0_write_valid;	// From u_vm5_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm5_rbank1_write_addr;// From u_vm5_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm5_rbank1_write_data;	// From u_vm5_slice of js_vm_eu_slice.v
output			vm5_rbank1_write_valid;	// From u_vm5_slice of js_vm_eu_slice.v
output			vm6_cc_update;		// From u_vm6_slice of js_vm_eu_slice.v
output			vm6_cc_update_value;	// From u_vm6_slice of js_vm_eu_slice.v
output [255:0]		vm6_eu_mh_data;		// From u_vm6_slice of js_vm_eu_slice.v
output [17:0]		vm6_eu_mh_index;	// From u_vm6_slice of js_vm_eu_slice.v
output			vm6_eu_mh_last;		// From u_vm6_slice of js_vm_eu_slice.v
output [3:0]		vm6_eu_mh_type;		// From u_vm6_slice of js_vm_eu_slice.v
output			vm6_eu_mh_valid;	// From u_vm6_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm6_rbank0_write_addr;// From u_vm6_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm6_rbank0_write_data;	// From u_vm6_slice of js_vm_eu_slice.v
output			vm6_rbank0_write_valid;	// From u_vm6_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm6_rbank1_write_addr;// From u_vm6_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm6_rbank1_write_data;	// From u_vm6_slice of js_vm_eu_slice.v
output			vm6_rbank1_write_valid;	// From u_vm6_slice of js_vm_eu_slice.v
output			vm7_cc_update;		// From u_vm7_slice of js_vm_eu_slice.v
output			vm7_cc_update_value;	// From u_vm7_slice of js_vm_eu_slice.v
output [255:0]		vm7_eu_mh_data;		// From u_vm7_slice of js_vm_eu_slice.v
output [17:0]		vm7_eu_mh_index;	// From u_vm7_slice of js_vm_eu_slice.v
output			vm7_eu_mh_last;		// From u_vm7_slice of js_vm_eu_slice.v
output [3:0]		vm7_eu_mh_type;		// From u_vm7_slice of js_vm_eu_slice.v
output			vm7_eu_mh_valid;	// From u_vm7_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm7_rbank0_write_addr;// From u_vm7_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm7_rbank0_write_data;	// From u_vm7_slice of js_vm_eu_slice.v
output			vm7_rbank0_write_valid;	// From u_vm7_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm7_rbank1_write_addr;// From u_vm7_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm7_rbank1_write_data;	// From u_vm7_slice of js_vm_eu_slice.v
output			vm7_rbank1_write_valid;	// From u_vm7_slice of js_vm_eu_slice.v
output			vm8_cc_update;		// From u_vm8_slice of js_vm_eu_slice.v
output			vm8_cc_update_value;	// From u_vm8_slice of js_vm_eu_slice.v
output [255:0]		vm8_eu_mh_data;		// From u_vm8_slice of js_vm_eu_slice.v
output [17:0]		vm8_eu_mh_index;	// From u_vm8_slice of js_vm_eu_slice.v
output			vm8_eu_mh_last;		// From u_vm8_slice of js_vm_eu_slice.v
output [3:0]		vm8_eu_mh_type;		// From u_vm8_slice of js_vm_eu_slice.v
output			vm8_eu_mh_valid;	// From u_vm8_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm8_rbank0_write_addr;// From u_vm8_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm8_rbank0_write_data;	// From u_vm8_slice of js_vm_eu_slice.v
output			vm8_rbank0_write_valid;	// From u_vm8_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm8_rbank1_write_addr;// From u_vm8_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm8_rbank1_write_data;	// From u_vm8_slice of js_vm_eu_slice.v
output			vm8_rbank1_write_valid;	// From u_vm8_slice of js_vm_eu_slice.v
output			vm9_cc_update;		// From u_vm9_slice of js_vm_eu_slice.v
output			vm9_cc_update_value;	// From u_vm9_slice of js_vm_eu_slice.v
output [255:0]		vm9_eu_mh_data;		// From u_vm9_slice of js_vm_eu_slice.v
output [17:0]		vm9_eu_mh_index;	// From u_vm9_slice of js_vm_eu_slice.v
output			vm9_eu_mh_last;		// From u_vm9_slice of js_vm_eu_slice.v
output [3:0]		vm9_eu_mh_type;		// From u_vm9_slice of js_vm_eu_slice.v
output			vm9_eu_mh_valid;	// From u_vm9_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm9_rbank0_write_addr;// From u_vm9_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm9_rbank0_write_data;	// From u_vm9_slice of js_vm_eu_slice.v
output			vm9_rbank0_write_valid;	// From u_vm9_slice of js_vm_eu_slice.v
output [GPR_ADDR_BITS-2:0] vm9_rbank1_write_addr;// From u_vm9_slice of js_vm_eu_slice.v
output [REG_WIDTH-1:0]	vm9_rbank1_write_data;	// From u_vm9_slice of js_vm_eu_slice.v
output			vm9_rbank1_write_valid;	// From u_vm9_slice of js_vm_eu_slice.v
input			debug_mh_ready;
input			vm0_eu_mh_ready;
input			vm1_eu_mh_ready;
input			vm2_eu_mh_ready;
input			vm3_eu_mh_ready;
input			vm4_eu_mh_ready;
input			vm5_eu_mh_ready;
input			vm6_eu_mh_ready;
input			vm7_eu_mh_ready;
input			vm8_eu_mh_ready;
input			vm9_eu_mh_ready;
input			vm10_eu_mh_ready;
input			vm11_eu_mh_ready;
input			vm12_eu_mh_ready;
input			vm13_eu_mh_ready;
input			vm14_eu_mh_ready;
input			vm15_eu_mh_ready;


/*AUTOINPUT*/

/*AUTOWIRE*/


wire  logic	[16-1:0] 					cc_update;// From u_warb of js_vm_eu_warb.v
wire  logic	[16-1:0] 					cc_update_value;// From u_warb of js_vm_eu_warb.v
wire  logic	[16*(GPR_ADDR_BITS-1)-1:0]	rbank0_write_addr;// From u_warb of js_vm_eu_warb.v
wire  logic	[16*REG_WIDTH-1:0] 			rbank0_write_data;// From u_warb of js_vm_eu_warb.v
wire  logic	[16-1:0] 					rbank0_write_valid;// From u_warb of js_vm_eu_warb.v
wire  logic	[16*(GPR_ADDR_BITS-1)-1:0]	rbank1_write_addr;// From u_warb of js_vm_eu_warb.v
wire  logic	[16*REG_WIDTH-1:0] 			rbank1_write_data;// From u_warb of js_vm_eu_warb.v
wire  logic	[16-1:0] 					rbank1_write_valid;// From u_warb of js_vm_eu_warb.v

wire  logic	[16-1:0]                 	eu_mh_valid;
wire  logic	[16*18-1:0]              	eu_mh_index;
wire  logic	[16*4-1:0]               	eu_mh_vm_id;
wire  logic	[16*256-1:0]             	eu_mh_data;
wire  logic	[16*4-1:0]               	eu_mh_type;
wire  logic	[16-1:0]                 	eu_mh_last;
wire  logic	[16-1:0]                 	eu_mh_ready;

assign {vm15_cc_update, vm14_cc_update, vm13_cc_update, vm12_cc_update,
		vm11_cc_update, vm10_cc_update, vm9_cc_update,  vm8_cc_update,
		vm7_cc_update,  vm6_cc_update,  vm5_cc_update,  vm4_cc_update,
		vm3_cc_update,  vm2_cc_update,  vm1_cc_update,  vm0_cc_update} = cc_update;
assign {vm15_cc_update_value, vm14_cc_update_value, vm13_cc_update_value, vm12_cc_update_value,
		vm11_cc_update_value, vm10_cc_update_value, vm9_cc_update_value,  vm8_cc_update_value,
		vm7_cc_update_value,  vm6_cc_update_value,  vm5_cc_update_value,  vm4_cc_update_value,
		vm3_cc_update_value,  vm2_cc_update_value,  vm1_cc_update_value,  vm0_cc_update_value} = cc_update_value;
assign {vm15_rbank0_write_valid, vm14_rbank0_write_valid, vm13_rbank0_write_valid, vm12_rbank0_write_valid,
		vm11_rbank0_write_valid, vm10_rbank0_write_valid, vm9_rbank0_write_valid,  vm8_rbank0_write_valid,
		vm7_rbank0_write_valid,  vm6_rbank0_write_valid,  vm5_rbank0_write_valid,  vm4_rbank0_write_valid,
		vm3_rbank0_write_valid,  vm2_rbank0_write_valid,  vm1_rbank0_write_valid,  vm0_rbank0_write_valid} = rbank0_write_valid;
assign {vm15_rbank0_write_addr, vm14_rbank0_write_addr, vm13_rbank0_write_addr, vm12_rbank0_write_addr,
		vm11_rbank0_write_addr, vm10_rbank0_write_addr, vm9_rbank0_write_addr,  vm8_rbank0_write_addr,
		vm7_rbank0_write_addr,  vm6_rbank0_write_addr,  vm5_rbank0_write_addr,  vm4_rbank0_write_addr,
		vm3_rbank0_write_addr,  vm2_rbank0_write_addr,  vm1_rbank0_write_addr,  vm0_rbank0_write_addr} = rbank0_write_addr;
assign {vm15_rbank0_write_data, vm14_rbank0_write_data, vm13_rbank0_write_data, vm12_rbank0_write_data,
		vm11_rbank0_write_data, vm10_rbank0_write_data, vm9_rbank0_write_data,  vm8_rbank0_write_data,
		vm7_rbank0_write_data,  vm6_rbank0_write_data,  vm5_rbank0_write_data,  vm4_rbank0_write_data,
		vm3_rbank0_write_data,  vm2_rbank0_write_data,  vm1_rbank0_write_data,  vm0_rbank0_write_data} = rbank0_write_data;
assign {vm15_rbank1_write_valid, vm14_rbank1_write_valid, vm13_rbank1_write_valid, vm12_rbank1_write_valid,
		vm11_rbank1_write_valid, vm10_rbank1_write_valid, vm9_rbank1_write_valid,  vm8_rbank1_write_valid,
		vm7_rbank1_write_valid,  vm6_rbank1_write_valid,  vm5_rbank1_write_valid,  vm4_rbank1_write_valid,
		vm3_rbank1_write_valid,  vm2_rbank1_write_valid,  vm1_rbank1_write_valid,  vm0_rbank1_write_valid} = rbank1_write_valid;
assign {vm15_rbank1_write_addr, vm14_rbank1_write_addr, vm13_rbank1_write_addr, vm12_rbank1_write_addr,
		vm11_rbank1_write_addr, vm10_rbank1_write_addr, vm9_rbank1_write_addr,  vm8_rbank1_write_addr,
		vm7_rbank1_write_addr,  vm6_rbank1_write_addr,  vm5_rbank1_write_addr,  vm4_rbank1_write_addr,
		vm3_rbank1_write_addr,  vm2_rbank1_write_addr,  vm1_rbank1_write_addr,  vm0_rbank1_write_addr} = rbank1_write_addr;
assign {vm15_rbank1_write_data, vm14_rbank1_write_data, vm13_rbank1_write_data, vm12_rbank1_write_data,
		vm11_rbank1_write_data, vm10_rbank1_write_data, vm9_rbank1_write_data,  vm8_rbank1_write_data,
		vm7_rbank1_write_data,  vm6_rbank1_write_data,  vm5_rbank1_write_data,  vm4_rbank1_write_data,
		vm3_rbank1_write_data,  vm2_rbank1_write_data,  vm1_rbank1_write_data,  vm0_rbank1_write_data} = rbank1_write_data;


assign {vm15_eu_mh_valid, vm14_eu_mh_valid, vm13_eu_mh_valid, vm12_eu_mh_valid,
		vm11_eu_mh_valid, vm10_eu_mh_valid, vm9_eu_mh_valid,  vm8_eu_mh_valid,
		vm7_eu_mh_valid,  vm6_eu_mh_valid,  vm5_eu_mh_valid,  vm4_eu_mh_valid,
		vm3_eu_mh_valid,  vm2_eu_mh_valid,  vm1_eu_mh_valid,  vm0_eu_mh_valid} = eu_mh_valid;
assign {vm15_eu_mh_index, vm14_eu_mh_index, vm13_eu_mh_index, vm12_eu_mh_index,
		vm11_eu_mh_index, vm10_eu_mh_index, vm9_eu_mh_index,  vm8_eu_mh_index,
		vm7_eu_mh_index,  vm6_eu_mh_index,  vm5_eu_mh_index,  vm4_eu_mh_index,
		vm3_eu_mh_index,  vm2_eu_mh_index,  vm1_eu_mh_index,  vm0_eu_mh_index} = eu_mh_index;
assign {vm15_eu_mh_type, vm14_eu_mh_type, vm13_eu_mh_type, vm12_eu_mh_type,
		vm11_eu_mh_type, vm10_eu_mh_type, vm9_eu_mh_type,  vm8_eu_mh_type,
		vm7_eu_mh_type,  vm6_eu_mh_type,  vm5_eu_mh_type,  vm4_eu_mh_type,
		vm3_eu_mh_type,  vm2_eu_mh_type,  vm1_eu_mh_type,  vm0_eu_mh_type} = eu_mh_type;
assign {vm15_eu_mh_data, vm14_eu_mh_data, vm13_eu_mh_data, vm12_eu_mh_data,
		vm11_eu_mh_data, vm10_eu_mh_data, vm9_eu_mh_data,  vm8_eu_mh_data,
		vm7_eu_mh_data,  vm6_eu_mh_data,  vm5_eu_mh_data,  vm4_eu_mh_data,
		vm3_eu_mh_data,  vm2_eu_mh_data,  vm1_eu_mh_data,  vm0_eu_mh_data} = eu_mh_data;
assign {vm15_eu_mh_last, vm14_eu_mh_last, vm13_eu_mh_last, vm12_eu_mh_last,
		vm11_eu_mh_last, vm10_eu_mh_last, vm9_eu_mh_last,  vm8_eu_mh_last,
		vm7_eu_mh_last,  vm6_eu_mh_last,  vm5_eu_mh_last,  vm4_eu_mh_last,
		vm3_eu_mh_last,  vm2_eu_mh_last,  vm1_eu_mh_last,  vm0_eu_mh_last} = eu_mh_last;
assign eu_mh_ready = {vm15_eu_mh_ready, vm14_eu_mh_ready, vm13_eu_mh_ready, vm12_eu_mh_ready,
					  vm11_eu_mh_ready, vm10_eu_mh_ready, vm9_eu_mh_ready,  vm8_eu_mh_ready,
					  vm7_eu_mh_ready,  vm6_eu_mh_ready,  vm5_eu_mh_ready,  vm4_eu_mh_ready,
					  vm3_eu_mh_ready,  vm2_eu_mh_ready,  vm1_eu_mh_ready,  vm0_eu_mh_ready};

wire	[EU_SLICE_NUM-1:0]		slice_debug_mh_valid;
wire	[EU_SLICE_NUM*256-1:0]	slice_debug_mh_data;
logic	[EU_SLICE_NUM-1:0]		slice_debug_mh_ready;

wire    dbg_ff_push;
wire    [255:0] dbg_ff_din;
wire    dbg_ff_pop;
wire    [255:0] dbg_ff_dout;
wire    dbg_ff_empty;
wire    dbg_ff_full;

always @* begin
    slice_debug_mh_ready = {EU_SLICE_NUM{1'b1}};
    slice_debug_mh_ready[aleo_cr_debug_id[3:2]] = !dbg_ff_full; //debug_mh_ready;
end

js_vm_sfifo #(.WIDTH(256), .DEPTH(2)) u_dbg_fifo (
    .clk    (clk),
    .rstn   (rstn),
    .push   (dbg_ff_push),
    .din    (dbg_ff_din),
    .pop    (dbg_ff_pop),
    .dout   (dbg_ff_dout),
    .empty  (dbg_ff_empty),
    .full   (dbg_ff_full)
);


//assign	slice_debug_mh_ready    = EU_SLICE_NUM==1 ? debug_mh_ready : {{(EU_SLICE_NUM-1){1'b1}}, debug_mh_ready};
wire dbg_valid = slice_debug_mh_valid[aleo_cr_debug_id[3:2]] && aleo_cr_debug_mode[1];
//assign debug_mh_data  = slice_debug_mh_data[256*aleo_cr_debug_id[3:2]+:256];
wire    [255:0] slice_debug_mh_data_array   [0:EU_SLICE_NUM-1];

wire    [255:0] dbg_data = slice_debug_mh_data_array[aleo_cr_debug_id[3:2]];
assign  dbg_ff_push = dbg_valid && !dbg_ff_full;
assign  dbg_ff_din = dbg_data;
//assign  debug_mh_valid = !dbg_ff_empty;
//assign  debug_mh_data  = dbg_ff_dout;
//assign  dbg_ff_pop     = debug_mh_valid && debug_mh_ready;

wire    dbg_ff_valid = !dbg_ff_empty;
wire    [255:0] dbg_ff_data = dbg_ff_dout;
wire    dbg_ff_ready;
assign  dbg_ff_pop = dbg_ff_valid && dbg_ff_ready;


// add regslice for timing
js_lib_regslice #(.D(256), .N(1)) u_dbg_mh_regslice (
    .clk        (clk),
    .rstn       (rstn),

    .i_valid    (dbg_ff_valid),
    .i_data     (dbg_ff_data),
    .i_ready    (dbg_ff_ready),
    .o_valid    (debug_mh_valid),
    .o_data     (debug_mh_data),
    .o_ready    (debug_mh_ready)
);




genvar i;
generate
for(i=0; i<EU_SLICE_NUM; i=i+1) begin
//----------------------------------------
/*js_vm_eu_slice AUTO_TEMPLATE (
    .slice_sq_\(.*\)_valid		(sq_\1_valids[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
    .slice_sq_\(.*\)_ready		(sq_\1_readys[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
    .slice_sq_\(.*\)_data		(sq_\1_datas[(i+1)*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:i*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)]),
    .slice_\(.*\)_sq_fc_dec		(\1_sq_fc_dec[(i+1)*VM_PER_SLICE*FC_NUM-1:i*VM_PER_SLICE*FC_NUM]),
    .slice_pap_sq_hq_rel_valid	(pap_sq_hq_rel_valid[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
    .slice_cc_update			(cc_update[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
    .slice_cc_update_value		(cc_update_value[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
    .slice_rbank0_write_valid	(rbank0_write_valid[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
    .slice_rbank0_write_addr	(rbank0_write_addr[(i+1)*VM_PER_SLICE*(GPR_ADDR_BITS-1)-1:(i)*VM_PER_SLICE*(GPR_ADDR_BITS-1)]),
    .slice_rbank0_write_data	(rbank0_write_data[(i+1)*VM_PER_SLICE*(REG_WIDTH)-1:(i)*VM_PER_SLICE*(REG_WIDTH)]),
    .slice_rbank1_write_valid	(rbank1_write_valid[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
    .slice_rbank1_write_addr	(rbank1_write_addr[(i+1)*VM_PER_SLICE*(GPR_ADDR_BITS-1)-1:(i)*VM_PER_SLICE*(GPR_ADDR_BITS-1)]),
    .slice_rbank1_write_data	(rbank1_write_data[(i+1)*VM_PER_SLICE*(REG_WIDTH)-1:(i)*VM_PER_SLICE*(REG_WIDTH)]),
    .slice_eu_mh_valid       	(eu_mh_valid[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
	.slice_eu_mh_index			(eu_mh_index[(i+1)*VM_PER_SLICE*18-1:(i)*VM_PER_SLICE*18]),
	.slice_eu_mh_data			(eu_mh_data[(i+1)*VM_PER_SLICE*256-1:(i)*VM_PER_SLICE*256]),
	.slice_eu_mh_type			(eu_mh_type[(i+1)*VM_PER_SLICE*4-1:(i)*VM_PER_SLICE*4]),
	.slice_eu_mh_last			(eu_mh_last[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
	.slice_eu_mh_ready			(eu_mh_ready[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]),
	.slice_eu_mh_vm_id			(),
	.debug_mh_valid				(slice_debug_mh_valid[i]),
	.debug_mh_data				(slice_debug_mh_data[(i+1)*256-1:i*256]),
	.debug_mh_ready				(slice_debug_mh_ready[i]),
);
*/

js_vm_eu_slice u_eu_slice (/*AUTOINST*/
			   // Outputs
			   .slice_sq_pap_ready	(sq_pap_readys[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_map_ready	(sq_map_readys[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_mip_ready	(sq_mip_readys[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_lgc_ready	(sq_lgc_readys[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_alu_ready	(sq_alu_readys[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_tbt_ready	(sq_tbt_readys[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_mov_ready	(sq_mov_readys[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_pap_sq_fc_dec	(pap_sq_fc_dec[(i+1)*VM_PER_SLICE*FC_NUM-1:i*VM_PER_SLICE*FC_NUM]), // Templated
			   .slice_map_sq_fc_dec	(map_sq_fc_dec[(i+1)*VM_PER_SLICE*FC_NUM-1:i*VM_PER_SLICE*FC_NUM]), // Templated
			   .slice_mip_sq_fc_dec	(mip_sq_fc_dec[(i+1)*VM_PER_SLICE*FC_NUM-1:i*VM_PER_SLICE*FC_NUM]), // Templated
			   .slice_lgc_sq_fc_dec	(lgc_sq_fc_dec[(i+1)*VM_PER_SLICE*FC_NUM-1:i*VM_PER_SLICE*FC_NUM]), // Templated
			   .slice_alu_sq_fc_dec	(alu_sq_fc_dec[(i+1)*VM_PER_SLICE*FC_NUM-1:i*VM_PER_SLICE*FC_NUM]), // Templated
			   .slice_tbt_sq_fc_dec	(tbt_sq_fc_dec[(i+1)*VM_PER_SLICE*FC_NUM-1:i*VM_PER_SLICE*FC_NUM]), // Templated
			   .slice_mov_sq_fc_dec	(mov_sq_fc_dec[(i+1)*VM_PER_SLICE*FC_NUM-1:i*VM_PER_SLICE*FC_NUM]), // Templated
			   .slice_pap_sq_hq_rel_valid(pap_sq_hq_rel_valid[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_cc_update	(cc_update[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_cc_update_value(cc_update_value[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_rbank0_write_addr(rbank0_write_addr[(i+1)*VM_PER_SLICE*(GPR_ADDR_BITS-1)-1:(i)*VM_PER_SLICE*(GPR_ADDR_BITS-1)]), // Templated
			   .slice_rbank0_write_data(rbank0_write_data[(i+1)*VM_PER_SLICE*(REG_WIDTH)-1:(i)*VM_PER_SLICE*(REG_WIDTH)]), // Templated
			   .slice_rbank0_write_valid(rbank0_write_valid[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_rbank1_write_addr(rbank1_write_addr[(i+1)*VM_PER_SLICE*(GPR_ADDR_BITS-1)-1:(i)*VM_PER_SLICE*(GPR_ADDR_BITS-1)]), // Templated
			   .slice_rbank1_write_data(rbank1_write_data[(i+1)*VM_PER_SLICE*(REG_WIDTH)-1:(i)*VM_PER_SLICE*(REG_WIDTH)]), // Templated
			   .slice_rbank1_write_valid(rbank1_write_valid[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_eu_mh_valid	(eu_mh_valid[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_eu_mh_index	(eu_mh_index[(i+1)*VM_PER_SLICE*18-1:(i)*VM_PER_SLICE*18]), // Templated
			   .slice_eu_mh_vm_id	(),		 // Templated
			   .slice_eu_mh_data	(eu_mh_data[(i+1)*VM_PER_SLICE*256-1:(i)*VM_PER_SLICE*256]), // Templated
			   .slice_eu_mh_type	(eu_mh_type[(i+1)*VM_PER_SLICE*4-1:(i)*VM_PER_SLICE*4]), // Templated
			   .slice_eu_mh_last	(eu_mh_last[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .debug_mh_valid	(slice_debug_mh_valid[i]), // Templated
			   .debug_mh_data	(slice_debug_mh_data[(i+1)*256-1:i*256]), // Templated
			   // Inputs
			   .clk			(clk),
			   .rstn		(rstn),
			   .aleo_cr_debug_mode	(aleo_cr_debug_mode[1:0]),
			   .aleo_cr_debug_id	(aleo_cr_debug_id[3:0]),
			   .aleo_cr_q		(aleo_cr_q[255:0]),
			   .aleo_cr_mu		(aleo_cr_mu[255:0]),
			   .slice_sq_pap_valid	(sq_pap_valids[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_pap_data	(sq_pap_datas[(i+1)*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:i*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)]), // Templated
			   .slice_sq_map_valid	(sq_map_valids[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_map_data	(sq_map_datas[(i+1)*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:i*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)]), // Templated
			   .slice_sq_mip_valid	(sq_mip_valids[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_mip_data	(sq_mip_datas[(i+1)*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:i*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)]), // Templated
			   .slice_sq_lgc_valid	(sq_lgc_valids[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_lgc_data	(sq_lgc_datas[(i+1)*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:i*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)]), // Templated
			   .slice_sq_alu_valid	(sq_alu_valids[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_alu_data	(sq_alu_datas[(i+1)*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:i*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)]), // Templated
			   .slice_sq_tbt_valid	(sq_tbt_valids[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_tbt_data	(sq_tbt_datas[(i+1)*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:i*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)]), // Templated
			   .slice_sq_mov_valid	(sq_mov_valids[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .slice_sq_mov_data	(sq_mov_datas[(i+1)*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:i*VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)]), // Templated
			   .slice_eu_mh_ready	(eu_mh_ready[(i+1)*VM_PER_SLICE-1:(i)*VM_PER_SLICE]), // Templated
			   .debug_mh_ready	(slice_debug_mh_ready[i])); // Templated
end
endgenerate

genvar k;
generate
    for(k=0; k<EU_SLICE_NUM; k=k+1) begin
        assign slice_debug_mh_data_array[k] = slice_debug_mh_data[k*256+:256];
    end
endgenerate
endmodule
// Verilog-mode Setting:
// Local Variables:
// verilog-library-directories: ("../sq/" "../regfile/" "./" "./bits/" "./integer/" "./mod/" "./macro" "./mod/inv" "./mod/mul")
// verilog-auto-inst-param-value: t
// End:

