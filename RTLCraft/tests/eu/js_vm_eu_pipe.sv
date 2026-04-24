module js_vm_eu_pipe (/*AUTOARG*/
   // Outputs
   slice_i_ready, slice_o_valid, slice_o_data, slice_o_mask,
   slice_o_fc_dec, slice_o_hq_rel_valid,
   // Inputs
   clk, rstn, aleo_cr_q, aleo_cr_mu, slice_i_valid, slice_i_data,
   slice_o_ready
   );
parameter   PIPE_TYPE = 0;  // 0: PAP, 1: MAP, 2: MIP, 3: LGC, 4: ALU, 5: MACRO, 6: MOV
`include "js_vm.vh"
input               clk;
input               rstn;
input	[255:0]	aleo_cr_q;
input	[255:0]	aleo_cr_mu;

input   [VM_PER_SLICE-1:0]                          slice_i_valid;
input   [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_i_data;
output  [VM_PER_SLICE-1:0]                          slice_i_ready;

output  [VM_PER_SLICE-1:0]                          slice_o_valid;
output  [VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0] slice_o_data;
output  [VM_PER_SLICE*2-1:0]                        slice_o_mask;
input   [VM_PER_SLICE-1:0]                          slice_o_ready;

output  [VM_PER_SLICE*FC_NUM-1:0]                        slice_o_fc_dec;

output  [VM_PER_SLICE-1:0]                          slice_o_hq_rel_valid;

localparam  ID_BITS = $clog2(VM_PER_SLICE);
//-----------------------------------------------
logic           pipe_i_valid;
logic   [4-1:0] pipe_i_vm_id;
logic   [(ISA_BITS+2*REG_WIDTH+1)-1:0]  pipe_i_data ;
logic           pipe_i_ready;
logic           pipe_i_valid_pre;
logic   [4-1:0] pipe_i_vm_id_pre;
logic   [(ISA_BITS+2*REG_WIDTH+1)-1:0]  pipe_i_data_pre ;
logic           pipe_i_ready_pre;

wire    [FC_NUM-1:0]   pipe_o_fc_dec;
wire    [3:0]   pipe_o_fc_dec_vm_id;
wire            pipe_o_valid;
wire    [ISA_BITS+REG_WIDTH+1-1:0]  pipe_o_data;
wire    [3:0]   pipe_o_vm_id;
wire            pipe_o_ready;
wire            pipe_o_hq_rel_valid;
wire    [3:0]   pipe_o_hq_rel_vm_id;
wire    [(ISA_BITS+2*REG_WIDTH+1)-1:0]  slice_i_data_array  [0:VM_PER_SLICE-1];
genvar i;
generate
if(PIPE_TYPE==0) begin  // PAP Pipe
assign  slice_o_mask = 'b0;
for(i=0; i<VM_PER_SLICE; i=i+1) begin
    assign slice_i_data_array[i] = slice_i_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)];
end

    if(VM_PER_SLICE==1) begin
        assign pipe_i_vm_id = 4'h0;
        assign pipe_i_valid = slice_i_valid;
        assign pipe_i_data  = slice_i_data;
        assign slice_i_ready = pipe_i_ready;

        assign slice_o_valid = pipe_o_valid;
        assign slice_o_data  = {{(REG_WIDTH){1'b0}}, pipe_o_data};
        assign pipe_o_ready  = slice_o_ready;

        assign slice_o_fc_dec = pipe_o_fc_dec;
        assign slice_o_hq_rel_valid = pipe_o_hq_rel_valid;
    end else begin
        assign pipe_i_data = slice_i_data_array[pipe_i_vm_id[ID_BITS-1:0]];
        assign slice_o_valid = pipe_o_valid ? {{(VM_PER_SLICE-1){1'b0}}, 1'b1} << pipe_o_vm_id[ID_BITS-1:0] : 'b0;
        assign slice_o_data  = {{((VM_PER_SLICE-1)*(VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1))){1'b0}}, {{(REG_WIDTH){1'b0}}, pipe_o_data}} << (pipe_o_vm_id[ID_BITS-1:0]*(ISA_BITS+2*REG_WIDTH+1));
        assign pipe_o_ready  = slice_o_ready[pipe_o_vm_id[ID_BITS-1:0]];
        assign slice_o_fc_dec = ~|pipe_o_fc_dec ? {(VM_PER_SLICE*FC_NUM){1'b0}} : {{(VM_PER_SLICE*FC_NUM-FC_NUM){1'b0}}, pipe_o_fc_dec} << (pipe_o_fc_dec_vm_id[ID_BITS-1:0]*FC_NUM);
        assign slice_o_hq_rel_valid = ~pipe_o_hq_rel_valid ? {(VM_PER_SLICE){1'b0}} : {{(VM_PER_SLICE-1){1'b0}}, pipe_o_hq_rel_valid} << pipe_o_hq_rel_vm_id[ID_BITS-1:0];
/*
js_vm_mux_arb AUTO_TEMPLATE "u_\(.*\)_iarb" (
	.in_valids	(slice_i_valid[]),
	.in_readys	(slice_i_ready[]),
	.grant_id	(pipe_i_vm_id[]),
	.out_valid	(pipe_i_valid),
	.out_ready	(pipe_i_ready),
);
*/
js_vm_mux_arb #(.NUM(VM_PER_SLICE), .ID_BITS(ID_BITS)) u_pipe_iarb (/*AUTOINST*/
								    // Outputs
								    .in_readys		(slice_i_ready[VM_PER_SLICE-1:0]), // Templated
								    .out_valid		(pipe_i_valid),	 // Templated
								    .grant_id		(pipe_i_vm_id[ID_BITS-1:0]), // Templated
								    // Inputs
								    .clk		(clk),
								    .rstn		(rstn),
								    .in_valids		(slice_i_valid[VM_PER_SLICE-1:0]), // Templated
								    .out_ready		(pipe_i_ready));	 // Templated
        if(VM_PER_SLICE!=16) begin
            assign pipe_i_vm_id[3:ID_BITS] = 'b0;
        end
    end
/*js_vm_pap_top AUTO_TEMPLATE (
	.sq_pap_q	(aleo_cr_q[]),
	.sq_pap_mu	(aleo_cr_mu[]),

    .sq_pap_valid   (pipe_i_valid),
    .sq_pap_data    (pipe_i_data[]),
    .sq_pap_vm_id   (pipe_i_vm_id[]),
    .sq_pap_ready   (pipe_i_ready),

    .pap_sq_\(.*\)  (pipe_o_\1[]),
	.pap_sq_res		(pipe_o_data[]),
	.clk			(pap_clk),
);
*/
wire	pap_clk;
wire	pap_active;
js_lib_clk_gater u_pap_icg (
	.clk	(clk),
	.rstn	(rstn),
	.active	(pap_active),
	.test_mode	(1'b0),
	.gated_clk	(pap_clk)
);

js_vm_pap_top u_pap (/*AUTOINST*/
		     // Outputs
		     .pap_active	(pap_active),
		     .sq_pap_ready	(pipe_i_ready),		 // Templated
		     .pap_sq_fc_dec	(pipe_o_fc_dec[FC_NUM-1:0]), // Templated
		     .pap_sq_fc_dec_vm_id(pipe_o_fc_dec_vm_id[3:0]), // Templated
		     .pap_sq_valid	(pipe_o_valid),		 // Templated
		     .pap_sq_res	(pipe_o_data[ISA_BITS+REG_WIDTH+1-1:0]), // Templated
		     .pap_sq_vm_id	(pipe_o_vm_id[3:0]),	 // Templated
		     .pap_sq_hq_rel_valid(pipe_o_hq_rel_valid),	 // Templated
		     .pap_sq_hq_rel_vm_id(pipe_o_hq_rel_vm_id[3:0]), // Templated
		     // Inputs
		     .clk		(pap_clk),		 // Templated
		     .rstn		(rstn),
		     .sq_pap_valid	(pipe_i_valid),		 // Templated
		     .sq_pap_data	(pipe_i_data[ISA_BITS+2*REG_WIDTH+1-1:0]), // Templated
		     .sq_pap_q		(aleo_cr_q[255:0]),	 // Templated
		     .sq_pap_mu		(aleo_cr_mu[255:0]),	 // Templated
		     .sq_pap_vm_id	(pipe_i_vm_id[3:0]),	 // Templated
		     .pap_sq_ready	(pipe_o_ready));		 // Templated

end else if(PIPE_TYPE==1) begin     // MAP Pipe
wire    [3:0]   slice_i_vm_id   [0:VM_PER_SLICE-1];
assign  slice_o_mask = 'b0;
assign  slice_o_hq_rel_valid = 'b0;
wire	[VM_PER_SLICE-1:0]	map_active;
wire	[VM_PER_SLICE-1:0]	map_clk;

    for(i=0; i<VM_PER_SLICE; i=i+1) begin
        assign slice_i_vm_id[i] = i;
js_lib_clk_gater u_map_icg (
	.clk	(clk),
	.rstn	(rstn),
	.active	(map_active[i]),
	.test_mode	(1'b0),
	.gated_clk	(map_clk[i])
);
js_vm_map_top u_map (
		     // Outputs
		     .sq_map_ready	(slice_i_ready[i]),
		     .map_sq_fc_dec	(slice_o_fc_dec[FC_NUM*i+:FC_NUM]),
		     .map_sq_fc_dec_vm_id(),
		     .map_sq_res	(slice_o_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]),
		     .map_sq_valid	(slice_o_valid[i]),
		     .map_sq_vm_id	(),
			 .map_active	(map_active[i]),
		     // Inputs
		     .clk		(map_clk[i]),
		     .rstn		(rstn),
		     .sq_map_valid	(slice_i_valid[i]),
		     .sq_map_data	(slice_i_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]),
		     .sq_map_modsub_q	(aleo_cr_q[DATA_WIDTH-1:0]),
		     .sq_map_modadd_q	(aleo_cr_q[DATA_WIDTH-1:0]),
		     .sq_map_vm_id	(slice_i_vm_id[i]),
		     .map_sq_ready	(slice_o_ready[i]));
    end
end else if(PIPE_TYPE==2) begin     // MIP Pipe
wire    [3:0]   slice_i_vm_id   [0:VM_PER_SLICE-1];
assign  slice_o_mask = 'b0;
assign  slice_o_hq_rel_valid = 'b0;

wire	[VM_PER_SLICE-1:0]	mip_slice_i_valid;
wire	[VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1)-1:0]	mip_slice_i_data;
wire	[3:0]	mip_slice_i_vm_id	[0:VM_PER_SLICE-1];
wire	[VM_PER_SLICE-1:0]	mip_slice_i_ready;
wire	[VM_PER_SLICE-1:0]	mip_infifo_pop;
wire	[VM_PER_SLICE-1:0]	mip_infifo_full;
wire	[VM_PER_SLICE-1:0]	mip_infifo_empty;
assign	slice_i_ready = ~mip_infifo_full;

wire	[VM_PER_SLICE-1:0]	mip_active;
wire	[VM_PER_SLICE-1:0]	mip_clk;

    for(i=0; i<VM_PER_SLICE; i=i+1) begin
        assign slice_i_vm_id[i] = i;
assign	mip_slice_i_valid[i] = !mip_infifo_empty[i];
assign	mip_infifo_pop[i] = mip_slice_i_valid[i] && mip_slice_i_ready[i];
js_vm_sfifo #(.WIDTH(4+(ISA_BITS+2*REG_WIDTH+1)), .DEPTH(4)) u_mip_infifo (
	.clk			(clk),
	.rstn			(rstn),
	.push			(slice_i_valid[i] && slice_i_ready[i]),
	.din			({slice_i_vm_id[i], slice_i_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]}),
	.pop			(mip_infifo_pop[i]),
	.dout			({mip_slice_i_vm_id[i], mip_slice_i_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]}),
	.empty			(mip_infifo_empty[i]),
	.full			(mip_infifo_full[i])
);
js_lib_clk_gater u_mip_icg (
	.clk	(clk),
	.rstn	(rstn),
	.active	(mip_active[i]),
	.test_mode	(1'b0),
	.gated_clk	(mip_clk[i])
);
js_vm_mip_top u_mip (
		     // Outputs
		     .sq_mip_ready	(mip_slice_i_ready[i]),
		     .mip_sq_fc_dec	(slice_o_fc_dec[FC_NUM*i+:FC_NUM]),
		     .mip_sq_fc_dec_vm_id(),
		     .mip_sq_res	(slice_o_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]),
		     .mip_sq_valid	(slice_o_valid[i]),
		     .mip_sq_vm_id	(),
			 .mip_active	(mip_active[i]),
		     // Inputs
		     .clk		(mip_clk[i]),
		     .rstn		(rstn),
		     .sq_mip_valid	(mip_slice_i_valid[i]),
		     .sq_mip_data	(mip_slice_i_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]),
		     .sq_mip_q	(aleo_cr_q[256-1:0]),
		     .sq_mip_vm_id	(mip_slice_i_vm_id[i]),
		     .mip_sq_ready	(slice_o_ready[i]));
    end
end else if(PIPE_TYPE==3) begin     // LGC Pipe
wire    [3:0]   slice_i_vm_id   [0:VM_PER_SLICE-1];
assign  slice_o_mask = 'b0;
assign  slice_o_hq_rel_valid = 'b0;

    for(i=0; i<VM_PER_SLICE; i=i+1) begin
        assign slice_i_vm_id[i] = i;
js_vm_logical u_logic(
		      // Outputs
		      .sq_logic_i_ready	(slice_i_ready[i]),
		      .sq_logic_o_valid	(slice_o_valid[i]),
		      .sq_logic_o_vm_id	(),
		      .sq_logic_res	(slice_o_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]),
		      .logic_sq_fc_dec	(slice_o_fc_dec[FC_NUM*i+:FC_NUM]),
		      .logic_sq_fc_dec_vm_id(),
		      // Inputs
		      .clk		(clk),
		      .rstn		(rstn),
		      .sq_logic_data	(slice_i_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]),
		      .sq_logic_i_valid	(slice_i_valid[i]),
		      .sq_logic_i_vm_id	(slice_i_vm_id[i]),
		      .sq_logic_o_ready	(slice_o_ready[i]));

    end
end else if(PIPE_TYPE==4) begin     // ALU Pipe
assign  slice_o_mask = 'b0;
for(i=0; i<VM_PER_SLICE; i=i+1) begin
    assign slice_i_data_array[i] = slice_i_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)];
end

    if(VM_PER_SLICE==1) begin
        assign pipe_i_vm_id = 4'h0;
        assign pipe_i_valid = slice_i_valid;
        assign pipe_i_data  = slice_i_data;
        assign slice_i_ready = pipe_i_ready;

        assign slice_o_valid = pipe_o_valid;
        assign slice_o_data  = {{(REG_WIDTH){1'b0}}, pipe_o_data};
        assign pipe_o_ready  = slice_o_ready;

        assign slice_o_fc_dec = pipe_o_fc_dec;
        assign slice_o_hq_rel_valid = 1'b0;
    end else begin
        assign pipe_i_data_pre = slice_i_data_array[pipe_i_vm_id_pre[ID_BITS-1:0]];
        assign slice_o_valid = pipe_o_valid ? {{(VM_PER_SLICE-1){1'b0}}, 1'b1} << pipe_o_vm_id[ID_BITS-1:0] : 'b0;
        assign slice_o_data  = {{((VM_PER_SLICE-1)*(VM_PER_SLICE*(ISA_BITS+2*REG_WIDTH+1))){1'b0}}, {{(REG_WIDTH){1'b0}}, pipe_o_data}} << (pipe_o_vm_id[ID_BITS-1:0]*(ISA_BITS+2*REG_WIDTH+1));
        assign pipe_o_ready  = slice_o_ready[pipe_o_vm_id[ID_BITS-1:0]];
        assign slice_o_fc_dec = ~|pipe_o_fc_dec ? {(VM_PER_SLICE*FC_NUM){1'b0}} : {{(VM_PER_SLICE*FC_NUM-FC_NUM){1'b0}}, pipe_o_fc_dec} << (pipe_o_fc_dec_vm_id[ID_BITS-1:0]*FC_NUM);
        assign slice_o_hq_rel_valid = 'b0;
/*
js_vm_mux_arb AUTO_TEMPLATE "u_\(.*\)_iarb" (
	.in_valids	(slice_i_valid[]),
	.in_readys	(slice_i_ready[]),
	.grant_id	(pipe_i_vm_id[]),
	.out_valid	(pipe_i_valid_pre),
	.out_ready	(pipe_i_ready_pre),
);
*/
js_vm_mux_arb #(.NUM(VM_PER_SLICE), .ID_BITS(ID_BITS)) u_pipe_iarb (/*AUTOINST*/
								    // Outputs
								    .in_readys		(slice_i_ready[VM_PER_SLICE-1:0]), // Templated
								    .out_valid		(pipe_i_valid_pre), // Templated
								    .grant_id		(pipe_i_vm_id_pre[ID_BITS-1:0]), // Templated
								    // Inputs
								    .clk		(clk),
								    .rstn		(rstn),
								    .in_valids		(slice_i_valid[VM_PER_SLICE-1:0]), // Templated
								    .out_ready		(pipe_i_ready_pre)); // Templated
        if(VM_PER_SLICE!=16) begin
            assign pipe_i_vm_id_pre[3:ID_BITS] = 'b0;
        end
    end

always @(posedge clk or negedge rstn)
if(!rstn)
	pipe_i_valid <= 1'b0;
else if(pipe_i_ready_pre)
	pipe_i_valid <= pipe_i_valid_pre;
assign pipe_i_ready_pre = pipe_i_ready || !pipe_i_valid;
always @(posedge clk)
if(pipe_i_valid_pre && pipe_i_ready_pre) begin
	pipe_i_vm_id <= pipe_i_vm_id_pre;
	pipe_i_data  <= pipe_i_data_pre;
end

/*js_vm_int AUTO_TEMPLATE (
    .int_and_i_valid   (pipe_i_valid),
    .int_and_data    (pipe_i_data[]),
    .int_and_i_vm_id   (pipe_i_vm_id[]),
    .int_and_i_ready   (pipe_i_ready),

	.int_and_o_valid	(pipe_o_valid),
	.int_and_o_vm_id	(pipe_o_vm_id[]),
	.int_and_o_ready	(pipe_o_ready),
	.int_and_res	(pipe_o_data[]),
	.int_sq_fc_dec	(pipe_o_fc_dec[]),
	.int_sq_fc_dec_vm_id	(pipe_o_fc_dec_vm_id[]),
	.clk		(int_clk),
);
*/
wire	int_clk;
wire	int_active;
js_lib_clk_gater u_int_icg (
	.clk	(clk),
	.rstn	(rstn),
	.active	(int_active),
	.test_mode	(1'b0),
	.gated_clk	(int_clk)
);
js_vm_int u_int (/*AUTOINST*/
		 // Outputs
		 .int_active		(int_active),
		 .int_and_i_ready	(pipe_i_ready),		 // Templated
		 .int_and_o_valid	(pipe_o_valid),		 // Templated
		 .int_and_o_vm_id	(pipe_o_vm_id[3:0]),	 // Templated
		 .int_and_res		(pipe_o_data[ISA_BITS+REG_WIDTH+1-1:0]), // Templated
		 .int_sq_fc_dec		(pipe_o_fc_dec[FC_NUM-1:0]), // Templated
		 .int_sq_fc_dec_vm_id	(pipe_o_fc_dec_vm_id[3:0]), // Templated
		 // Inputs
		 .clk			(int_clk),		 // Templated
		 .rstn			(rstn),
		 .int_and_data		(pipe_i_data[ISA_BITS+2*REG_WIDTH+1-1:0]), // Templated
		 .int_and_i_valid	(pipe_i_valid),		 // Templated
		 .int_and_o_ready	(pipe_o_ready),		 // Templated
		 .int_and_i_vm_id	(pipe_i_vm_id[3:0]));	 // Templated
end else if(PIPE_TYPE==5) begin     // MACRO Pipe
wire    [3:0]   slice_i_vm_id   [0:VM_PER_SLICE-1];
assign  slice_o_hq_rel_valid = 'b0;
wire	[VM_PER_SLICE-1:0]	mac_active;
wire	[VM_PER_SLICE-1:0]	mac_clk;
    for(i=0; i<VM_PER_SLICE; i=i+1) begin
        assign slice_i_vm_id[i] = i;
js_lib_clk_gater u_mac_icg (
	.clk	(clk),
	.rstn	(rstn),
	.active	(mac_active[i]),
	.test_mode	(1'b0),
	.gated_clk	(mac_clk[i])
);
js_vm_macro_top u_macro (
			 // Outputs
			 .sq_mac_ready		(slice_i_ready[i]),
			 .mac_sq_res		(slice_o_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]),
			 .mac_sq_valid		(slice_o_valid[i]),
			 .mac_sq_vm_id		(),
			 .mac_sq_mask		(slice_o_mask[2*i+:2]),
			 .mac_sq_fc_dec		(slice_o_fc_dec[FC_NUM*i+:FC_NUM]),
			 .mac_sq_fc_dec_vm_id	(),
			 .mac_active	(mac_active[i]),
			 // Inputs
			 .clk			(mac_clk[i]),
			 .rstn			(rstn),
			 .sq_mac_valid		(slice_i_valid[i]),
			 .sq_mac_data		(slice_i_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]),
			 .sq_mac_vm_id		(slice_i_vm_id[i]),
			 .mac_sq_ready		(slice_o_ready[i]));
    end
end else if(PIPE_TYPE==6) begin     // MOV Pipe
wire    [3:0]   slice_i_vm_id   [0:VM_PER_SLICE-1];
assign  slice_o_mask = 'b0;
assign  slice_o_hq_rel_valid = 'b0;

    for(i=0; i<VM_PER_SLICE; i=i+1) begin
        assign slice_i_vm_id[i] = i;

js_vm_mov u_mov (
		 // Outputs
		 .sq_mov_ready	(slice_i_ready[i]),
		 .mov_sq_fc_dec		(slice_o_fc_dec[FC_NUM*i+:FC_NUM]),
		 .mov_sq_fc_dec_vm_id	(),
		 .mov_res_valid	(slice_o_valid[i]),
		 .mov_res_vm_id	(),
		 .mov_res_data		(slice_o_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+REG_WIDTH+1)]),
		 // Inputs
		 .clk			(clk),
		 .rstn			(rstn),
		 .sq_mov_valid	(slice_i_valid[i]),
		 .sq_mov_data		(slice_i_data[i*(ISA_BITS+2*REG_WIDTH+1)+:(ISA_BITS+2*REG_WIDTH+1)]),
		 .sq_mov_vm_id	(slice_i_vm_id[i]),
		 .mov_res_ready	(slice_o_ready[i]));
    end
end

endgenerate








endmodule
// Verilog-mode Setting:
// Local Variables:
// verilog-library-directories: ("../sq/" "../regfile/" "./" "../eu/bits/" "../eu/integer/" "../eu/mod/" "../eu/macro" "../eu/mod/inv" "../eu/mod/mul" "../eu")
// verilog-auto-inst-param-value: t
// End:

