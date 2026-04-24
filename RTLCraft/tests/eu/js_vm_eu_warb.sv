module js_vm_eu_warb (/*AUTOARG*/
   // Outputs
   pap_sq_ready, lgc_sq_ready, map_sq_ready, mac_sq_ready,
   alu_sq_ready, mip_sq_ready, mov_sq_ready, cc_update,
   cc_update_value, rbank0_write_addr, rbank0_write_data,
   rbank0_write_valid, rbank1_write_addr, rbank1_write_data,
   rbank1_write_valid, eu_mh_valid, eu_mh_index, eu_mh_vm_id,
   eu_mh_data, eu_mh_type, eu_mh_last, debug_mh_valid, debug_mh_data,
   // Inputs
   clk, rstn, aleo_cr_debug_id, aleo_cr_debug_mode, pap_sq_valid,
   pap_sq_res, lgc_sq_valid, lgc_sq_res, map_sq_valid, map_sq_res,
   mac_sq_valid, mac_sq_mask, mac_sq_res, alu_sq_valid, alu_sq_res,
   mip_sq_valid, mip_sq_res, mov_sq_valid, mov_sq_res, eu_mh_ready,
   debug_mh_ready
   );
`include "js_vm.vh"
input           clk;
input           rstn;

input	[3:0]	aleo_cr_debug_id;
input   [1:0]   aleo_cr_debug_mode;

input                               pap_sq_valid;
input   [ISA_BITS+REG_WIDTH+1-1:0]  pap_sq_res;
output                              pap_sq_ready;

input                               lgc_sq_valid;
input   [ISA_BITS+REG_WIDTH+1-1:0]  lgc_sq_res;
output                              lgc_sq_ready;

input                               map_sq_valid;
input   [ISA_BITS+REG_WIDTH+1-1:0]  map_sq_res;
output                              map_sq_ready;

input                               mac_sq_valid;
input   [1:0]                       mac_sq_mask;
input   [ISA_BITS+2*REG_WIDTH+1-1:0]  mac_sq_res;
output                              mac_sq_ready;

input                               alu_sq_valid;
input   [ISA_BITS+REG_WIDTH+1-1:0]  alu_sq_res;
output                              alu_sq_ready;

input                               mip_sq_valid;
input   [ISA_BITS+REG_WIDTH+1-1:0]  mip_sq_res;
output                              mip_sq_ready;

input                               mov_sq_valid;
input   [ISA_BITS+REG_WIDTH+1-1:0]  mov_sq_res;
output                              mov_sq_ready;


output logic			                cc_update;		// To u_gpr of js_vm_gpr_top.v
output logic    		                cc_update_value;	// To u_gpr of js_vm_gpr_top.v
output logic    [(GPR_ADDR_BITS-1)-1:0] rbank0_write_addr;// To u_gpr of js_vm_gpr_top.v
output logic    [REG_WIDTH-1:0]         rbank0_write_data;	// To u_gpr of js_vm_gpr_top.v
output logic			                rbank0_write_valid;	// To u_gpr of js_vm_gpr_top.v
output logic    [(GPR_ADDR_BITS-1)-1:0] rbank1_write_addr;// To u_gpr of js_vm_gpr_top.v
output logic    [REG_WIDTH-1:0]	        rbank1_write_data;	// To u_gpr of js_vm_gpr_top.v
output logic	                        rbank1_write_valid;	// To u_gpr of js_vm_gpr_top.v


output logic                            eu_mh_valid;
output logic    [18-1:0]                eu_mh_index;
output logic    [4-1:0]                 eu_mh_vm_id;
output logic    [256-1:0]               eu_mh_data;
output logic    [4-1:0]                 eu_mh_type;
output logic                            eu_mh_last;
input  logic                            eu_mh_ready;

output				debug_mh_valid;
output	[255:0]		debug_mh_data;
input				debug_mh_ready;
//-----------------------------------------------------------------
/*AUTOWIRE*/


wire    [ISA_DST_FMT_BITS-1:0]  pap_res_fmt;
wire    [1:0]                   pap_res_type;
wire    [ISA_OPCODE_BITS-1:0]   pap_res_opcode;
wire                            pap_res_cc;
wire    [GPR_ADDR_BITS-1:0]     pap_res_addr;
wire    [REG_WIDTH-1:0]         pap_res_data;
assign {pap_res_fmt, pap_res_type, pap_res_opcode, pap_res_cc, pap_res_addr, pap_res_data} = extract_one_dst(pap_sq_res);

wire    [ISA_DST_FMT_BITS-1:0]  lgc_res_fmt;
wire    [1:0]                   lgc_res_type;
wire    [ISA_OPCODE_BITS-1:0]   lgc_res_opcode;
wire                            lgc_res_cc;
wire    [GPR_ADDR_BITS-1:0]     lgc_res_addr;
wire    [REG_WIDTH-1:0]         lgc_res_data;
assign {lgc_res_fmt, lgc_res_type, lgc_res_opcode, lgc_res_cc, lgc_res_addr, lgc_res_data} = extract_one_dst(lgc_sq_res);

wire    [ISA_DST_FMT_BITS-1:0]  alu_res_fmt;
wire    [1:0]                   alu_res_type;
wire    [ISA_OPCODE_BITS-1:0]   alu_res_opcode;
wire                            alu_res_cc;
wire    [GPR_ADDR_BITS-1:0]     alu_res_addr;
wire    [REG_WIDTH-1:0]         alu_res_data;
assign {alu_res_fmt, alu_res_type, alu_res_opcode, alu_res_cc, alu_res_addr, alu_res_data} = extract_one_dst(alu_sq_res);

wire    [ISA_DST_FMT_BITS-1:0]  map_res_fmt;
wire    [1:0]                   map_res_type;
wire    [ISA_OPCODE_BITS-1:0]   map_res_opcode;
wire                            map_res_cc;
wire    [GPR_ADDR_BITS-1:0]     map_res_addr;
wire    [REG_WIDTH-1:0]         map_res_data;
assign {map_res_fmt, map_res_type, map_res_opcode, map_res_cc, map_res_addr, map_res_data} = extract_one_dst(map_sq_res);

wire    [ISA_DST_FMT_BITS-1:0]  mip_res_fmt;
wire    [1:0]                   mip_res_type;
wire    [ISA_OPCODE_BITS-1:0]   mip_res_opcode;
wire                            mip_res_cc;
wire    [GPR_ADDR_BITS-1:0]     mip_res_addr;
wire    [REG_WIDTH-1:0]         mip_res_data;
assign {mip_res_fmt, mip_res_type, mip_res_opcode, mip_res_cc, mip_res_addr, mip_res_data} = extract_one_dst(mip_sq_res);

wire    [1:0]                   mac_res_type;
wire                            mac_res_cc;
wire    [GPR_ADDR_BITS-1:0]     mac_res0_addr;
wire    [REG_WIDTH-1:0]         mac_res0_data;
wire    [GPR_ADDR_BITS-1:0]     mac_res1_addr;
wire    [REG_WIDTH-1:0]         mac_res1_data;
assign {mac_res_type, mac_res_cc, mac_res1_addr, mac_res1_data, mac_res0_addr, mac_res0_data} = extract_two_dst(mac_sq_res);

wire    [ISA_DST_FMT_BITS-1:0]  mov_res_fmt;
wire    [1:0]                   mov_res_type;
wire    [ISA_OPCODE_BITS-1:0]   mov_res_opcode;
wire                            mov_res_cc;
wire    [GPR_ADDR_BITS-1:0]     mov_res_addr;
wire    [REG_WIDTH-1:0]         mov_res_data;
assign {mov_res_fmt, mov_res_type, mov_res_opcode, mov_res_cc, mov_res_addr, mov_res_data} = extract_one_dst(mov_sq_res);
wire                            mov_res_merkel_bit;
wire    [7:0]                   mov_res_merkel_num;
assign {mov_res_merkel_bit, mov_res_merkel_num} = extract_merkel(mov_sq_res);

//---------------------------------------------------------------
localparam MAC_GPR_IDLE = 2'b00;
localparam MAC_GPR_DST0 = 2'b01;
localparam MAC_GPR_DST1 = 2'b10;

reg [1:0]   mac_gpr_st, mac_gpr_st_nxt;
always @(posedge clk or negedge rstn)
if(!rstn)
    mac_gpr_st  <= MAC_GPR_IDLE;
else
    mac_gpr_st  <= mac_gpr_st_nxt;

reg mac_gpr_ready;
reg mac_gpr_valid0;
reg mac_gpr_valid1;
wire    mac_gpr_ready0;
wire    mac_gpr_ready1;
always @* begin
    mac_gpr_st_nxt = mac_gpr_st;
    mac_gpr_ready = 1'b0;
    mac_gpr_valid0 = 1'b0;
    mac_gpr_valid1 = 1'b0;
    case(mac_gpr_st)
        MAC_GPR_IDLE: begin
            if(mac_sq_valid && mac_res_type==2'b00) begin
                mac_gpr_valid0 = mac_sq_mask[0];
                mac_gpr_valid1 = mac_sq_mask[1];
                if(mac_sq_mask==2'b00)
                    mac_gpr_st_nxt = MAC_GPR_IDLE;
                else if(mac_sq_mask==2'b01 && mac_gpr_ready0) begin
                    mac_gpr_st_nxt = MAC_GPR_IDLE;
                    mac_gpr_ready  = 1'b1;
                end
                else if(mac_sq_mask==2'b10 && mac_gpr_ready1) begin
                    mac_gpr_st_nxt = MAC_GPR_IDLE;
                    mac_gpr_ready  = 1'b1;
                end
                else if(mac_sq_mask==2'b11) begin
                    if(mac_gpr_ready0 && mac_gpr_ready1)
                        mac_gpr_ready = 1'b1;
                    else if(mac_gpr_ready0)
                        mac_gpr_st_nxt = MAC_GPR_DST1;
                    else if(mac_gpr_ready1)
                        mac_gpr_st_nxt = MAC_GPR_DST0;
                end
            end
        end
        MAC_GPR_DST0: begin
            mac_gpr_valid0 = 1'b1;
            if(mac_gpr_ready0) begin
                mac_gpr_ready = 1'b1;
                mac_gpr_st_nxt = MAC_GPR_IDLE;
            end
        end
        MAC_GPR_DST1: begin
            mac_gpr_valid1 = 1'b1;
            if(mac_gpr_ready1) begin
                mac_gpr_ready = 1'b1;
                mac_gpr_st_nxt = MAC_GPR_IDLE;
            end
        end
        default: mac_gpr_st_nxt= MAC_GPR_IDLE;
    endcase

end


//---------------------------------------------------------------
wire    pipe0_gpr_bank0_valid;
wire    pipe1_gpr_bank0_valid;
wire    pipe2_gpr_bank0_valid;
wire    pipe3_gpr_bank0_valid;
wire    pipe4_gpr_bank0_valid;
wire    pipe5_gpr_bank0_valid;
wire    pipe6_gpr_bank0_valid;
wire    pipe7_gpr_bank0_valid;

wire    pipe0_gpr_bank1_valid;
wire    pipe1_gpr_bank1_valid;
wire    pipe2_gpr_bank1_valid;
wire    pipe3_gpr_bank1_valid;
wire    pipe4_gpr_bank1_valid;
wire    pipe5_gpr_bank1_valid;
wire    pipe6_gpr_bank1_valid;
wire    pipe7_gpr_bank1_valid;


assign  pipe0_gpr_bank0_valid = pap_sq_valid && pap_res_type==2'b00 && pap_res_fmt==4'hc && !pap_res_addr[0];
assign  pipe1_gpr_bank0_valid = map_sq_valid && map_res_type==2'b00 && (map_res_opcode==OPCODE_MADD ? (map_res_fmt==4'hc || map_res_fmt==4'hd):1'b1) && !map_res_addr[0];
assign  pipe2_gpr_bank0_valid = mip_sq_valid && mip_res_type==2'b00 && !mip_res_addr[0];
assign  pipe3_gpr_bank0_valid = alu_sq_valid && alu_res_type==2'b00 && !alu_res_addr[0];
assign  pipe4_gpr_bank0_valid = lgc_sq_valid && lgc_res_type==2'b00 && !lgc_res_addr[0];
assign  pipe5_gpr_bank0_valid = mov_sq_valid && mov_res_type==2'b00 && !mov_res_addr[0];
assign  pipe6_gpr_bank0_valid = mac_gpr_valid0 && !mac_res0_addr[0];
assign  pipe7_gpr_bank0_valid = mac_gpr_valid1 && !mac_res1_addr[0];

assign  pipe0_gpr_bank1_valid = pap_sq_valid && pap_res_type==2'b00 && pap_res_fmt==4'hc && pap_res_addr[0];
assign  pipe1_gpr_bank1_valid = map_sq_valid && map_res_type==2'b00 && (map_res_opcode==OPCODE_MADD ? (map_res_fmt==4'hc || map_res_fmt==4'hd):1'b1) && map_res_addr[0];
assign  pipe2_gpr_bank1_valid = mip_sq_valid && mip_res_type==2'b00 && mip_res_addr[0];
assign  pipe3_gpr_bank1_valid = alu_sq_valid && alu_res_type==2'b00 && alu_res_addr[0];
assign  pipe4_gpr_bank1_valid = lgc_sq_valid && lgc_res_type==2'b00 && lgc_res_addr[0];
assign  pipe5_gpr_bank1_valid = mov_sq_valid && mov_res_type==2'b00 && mov_res_addr[0];
assign  pipe6_gpr_bank1_valid = mac_gpr_valid0 && mac_res0_addr[0];
assign  pipe7_gpr_bank1_valid = mac_gpr_valid1 && mac_res1_addr[0];


//wire    pipe0_mh_valid = pap_sq_valid && pap_res_type==2'b10;
//wire    pipe1_mh_valid = map_sq_valid && map_res_type==2'b10;
//wire    pipe2_mh_valid = mip_sq_valid && mip_res_type==2'b10;
//wire    pipe3_mh_valid = alu_sq_valid && alu_res_type==2'b10;
//wire    pipe4_mh_valid = lgc_sq_valid && lgc_res_type==2'b10;
//wire    pipe5_mh_valid = mov_sq_valid && mov_res_type==2'b10;
//wire    pipe6_mh_valid = mac_sq_valid && mac_res_type==2'b10;
//----------------
// GPR update
wire    pipe0_gpr_bank0_ready;
wire    pipe0_gpr_bank1_ready;
wire    pipe1_gpr_bank0_ready;
wire    pipe1_gpr_bank1_ready;
wire    pipe2_gpr_bank0_ready;
wire    pipe2_gpr_bank1_ready;
wire    pipe3_gpr_bank0_ready;
wire    pipe3_gpr_bank1_ready;
wire    pipe4_gpr_bank0_ready;
wire    pipe4_gpr_bank1_ready;
wire    pipe5_gpr_bank0_ready;
wire    pipe5_gpr_bank1_ready;
wire    pipe6_gpr_bank0_ready;
wire    pipe6_gpr_bank1_ready;
wire    pipe7_gpr_bank0_ready;
wire    pipe7_gpr_bank1_ready;

assign mac_gpr_ready0 = mac_res0_addr[0] ? (|pipe6_gpr_bank1_ready) : (|pipe6_gpr_bank0_ready);
assign mac_gpr_ready1 = mac_res1_addr[0] ? (|pipe7_gpr_bank1_ready) : (|pipe7_gpr_bank0_ready);


wire    pap_gpr_ready = pap_res_fmt==4'hc ? (pap_res_addr[0] ? (|pipe0_gpr_bank1_ready) : (|pipe0_gpr_bank0_ready)) : 1'b1;
wire    map_gpr_ready = (map_res_opcode==OPCODE_MSUB || map_res_opcode==OPCODE_MADD || (map_res_opcode==OPCODE_MADD_ACC && (map_res_fmt==4'hc || map_res_fmt==4'hd))) ? (map_res_addr[0] ? (|pipe1_gpr_bank1_ready) : (|pipe1_gpr_bank0_ready)) : 1'b1;
wire    mip_gpr_ready = mip_res_addr[0] ? (|pipe2_gpr_bank1_ready) : (|pipe2_gpr_bank0_ready);
wire    alu_gpr_ready = alu_res_addr[0] ? (|pipe3_gpr_bank1_ready) : (|pipe3_gpr_bank0_ready);
wire    lgc_gpr_ready = lgc_res_addr[0] ? (|pipe4_gpr_bank1_ready) : (|pipe4_gpr_bank0_ready);
wire    mov_gpr_ready = mov_res_addr[0] ? (|pipe5_gpr_bank1_ready) : (|pipe5_gpr_bank0_ready);




wire    [7:0]   gpr_bank0_valids;
wire    [7:0]   gpr_bank1_valids;
wire    [7:0]   cc_updates      ;
wire    [7:0]   merkel_valids   ;


wire    [7:0]   slice_rbank0_valids;
wire    [7:0]   slice_rbank1_valids;
wire    [7:0]   slice_rbank0_readys;
wire    [7:0]   slice_rbank1_readys;

wire    slice_rbank0_rrb_valid;
wire    slice_rbank1_rrb_valid;
wire    [2:0]   slice_rbank0_sel;
wire    [2:0]   slice_rbank1_sel;

wire    [(GPR_ADDR_BITS-1)-1:0]    slice_rbank0_rrb_addr;
wire    [(GPR_ADDR_BITS-1)-1:0]    slice_rbank1_rrb_addr;
wire    [(REG_WIDTH)-1:0]          slice_rbank0_rrb_data;
wire    [(REG_WIDTH)-1:0]          slice_rbank1_rrb_data;



assign pipe0_gpr_bank0_ready = slice_rbank0_readys[0];
assign pipe0_gpr_bank1_ready = slice_rbank1_readys[0];
assign pipe1_gpr_bank0_ready = slice_rbank0_readys[1];
assign pipe1_gpr_bank1_ready = slice_rbank1_readys[1];
assign pipe2_gpr_bank0_ready = slice_rbank0_readys[2];
assign pipe2_gpr_bank1_ready = slice_rbank1_readys[2];
assign pipe3_gpr_bank0_ready = slice_rbank0_readys[3];
assign pipe3_gpr_bank1_ready = slice_rbank1_readys[3];
assign pipe4_gpr_bank0_ready = slice_rbank0_readys[4];
assign pipe4_gpr_bank1_ready = slice_rbank1_readys[4];
assign pipe5_gpr_bank0_ready = slice_rbank0_readys[5];
assign pipe5_gpr_bank1_ready = slice_rbank1_readys[5];
assign pipe6_gpr_bank0_ready = slice_rbank0_readys[6];
assign pipe6_gpr_bank1_ready = slice_rbank1_readys[6];
assign pipe7_gpr_bank0_ready = slice_rbank0_readys[7];
assign pipe7_gpr_bank1_ready = slice_rbank1_readys[7];

assign slice_rbank0_valids = {pipe7_gpr_bank0_valid, pipe6_gpr_bank0_valid, pipe5_gpr_bank0_valid, pipe4_gpr_bank0_valid,
                              pipe3_gpr_bank0_valid, pipe2_gpr_bank0_valid, pipe1_gpr_bank0_valid, pipe0_gpr_bank0_valid};
assign slice_rbank1_valids = {pipe7_gpr_bank1_valid, pipe6_gpr_bank1_valid, pipe5_gpr_bank1_valid, pipe4_gpr_bank1_valid,
                              pipe3_gpr_bank1_valid, pipe2_gpr_bank1_valid, pipe1_gpr_bank1_valid, pipe0_gpr_bank1_valid};

js_vm_rr_arb #(.NUM(8), .ID_BITS(3)) u_slice_rbank0_rrb (
						       // Outputs
						       .in_readys	(slice_rbank0_readys[7:0]),
						       .out_valid	(slice_rbank0_rrb_valid),
						       .grant_id	(slice_rbank0_sel[2:0]),
						       // Inputs
						       .clk		(clk),
						       .rstn		(rstn),
						       .in_valids	(slice_rbank0_valids[7:0]),
						       .out_ready	(1'b1));

js_vm_rr_arb #(.NUM(8), .ID_BITS(3)) u_slice_rbank1_rrb (
						       // Outputs
						       .in_readys	(slice_rbank1_readys[7:0]),
						       .out_valid	(slice_rbank1_rrb_valid),
						       .grant_id	(slice_rbank1_sel[2:0]),
						       // Inputs
						       .clk		(clk),
						       .rstn		(rstn),
						       .in_valids	(slice_rbank1_valids[7:0]),
						       .out_ready	(1'b1));
    
assign slice_rbank0_rrb_addr[(GPR_ADDR_BITS-1)-1:0] =   slice_rbank0_sel == 3'd0 ? pap_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank0_sel == 3'd1 ? map_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank0_sel == 3'd2 ? mip_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank0_sel == 3'd3 ? alu_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank0_sel == 3'd4 ? lgc_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank0_sel == 3'd5 ? mov_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank0_sel == 3'd6 ? mac_res0_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank0_sel == 3'd7 ? mac_res1_addr[GPR_ADDR_BITS-1:1] : 'b0;
assign slice_rbank1_rrb_addr[(GPR_ADDR_BITS-1)-1:0] =   slice_rbank1_sel == 3'd0 ? pap_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank1_sel == 3'd1 ? map_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank1_sel == 3'd2 ? mip_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank1_sel == 3'd3 ? alu_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank1_sel == 3'd4 ? lgc_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank1_sel == 3'd5 ? mov_res_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank1_sel == 3'd6 ? mac_res0_addr[GPR_ADDR_BITS-1:1] :
                                                        slice_rbank1_sel == 3'd7 ? mac_res1_addr[GPR_ADDR_BITS-1:1] : 'b0;
assign slice_rbank0_rrb_data[(REG_WIDTH)-1:0] = slice_rbank0_sel == 3'd0 ? pap_res_data[REG_WIDTH-1:0] :
                                                slice_rbank0_sel == 3'd1 ? map_res_data[REG_WIDTH-1:0] :
                                                slice_rbank0_sel == 3'd2 ? mip_res_data[REG_WIDTH-1:0] :
                                                slice_rbank0_sel == 3'd3 ? alu_res_data[REG_WIDTH-1:0] :
                                                slice_rbank0_sel == 3'd4 ? lgc_res_data[REG_WIDTH-1:0] :
                                                slice_rbank0_sel == 3'd5 ? mov_res_data[REG_WIDTH-1:0] :
                                                slice_rbank0_sel == 3'd6 ? mac_res0_data[REG_WIDTH-1:0] :
                                                slice_rbank0_sel == 3'd7 ? mac_res1_data[REG_WIDTH-1:0] : 'b0;
assign slice_rbank1_rrb_data[(REG_WIDTH)-1:0] = slice_rbank1_sel == 3'd0 ? pap_res_data[REG_WIDTH-1:0] :
                                                slice_rbank1_sel == 3'd1 ? map_res_data[REG_WIDTH-1:0] :
                                                slice_rbank1_sel == 3'd2 ? mip_res_data[REG_WIDTH-1:0] :
                                                slice_rbank1_sel == 3'd3 ? alu_res_data[REG_WIDTH-1:0] :
                                                slice_rbank1_sel == 3'd4 ? lgc_res_data[REG_WIDTH-1:0] :
                                                slice_rbank1_sel == 3'd5 ? mov_res_data[REG_WIDTH-1:0] :
                                                slice_rbank1_sel == 3'd6 ? mac_res0_data[REG_WIDTH-1:0] :
                                                slice_rbank1_sel == 3'd7 ? mac_res1_data[REG_WIDTH-1:0] : 'b0;
/* yyy remove one pipe
always @(posedge clk or negedge rstn)
if(!rstn) begin
    rbank0_write_valid <= 1'b0;
    rbank1_write_valid <= 1'b0;
end else begin
    rbank0_write_valid <= slice_rbank0_rrb_valid;
    rbank1_write_valid <= slice_rbank1_rrb_valid;
end
always @(posedge clk) begin
if(slice_rbank0_rrb_valid) begin
    rbank0_write_addr    <= slice_rbank0_rrb_addr;
    rbank0_write_data    <= slice_rbank0_rrb_data;
end
if(slice_rbank1_rrb_valid) begin
    rbank1_write_addr    <= slice_rbank1_rrb_addr;
    rbank1_write_data    <= slice_rbank1_rrb_data;
end
end
*/
always @* begin
    rbank1_write_valid = slice_rbank1_rrb_valid;
    rbank0_write_valid = slice_rbank0_rrb_valid;
    rbank0_write_data    = slice_rbank0_rrb_data;
    rbank0_write_addr    = slice_rbank0_rrb_addr;
    rbank1_write_data    = slice_rbank1_rrb_data;
    rbank1_write_addr    = slice_rbank1_rrb_addr;
end

//----------------
// CC update
/*
wire    [15:0]  pipe0_cc_readys = {vm15_cc_readys[0], vm14_cc_readys[0], vm13_cc_readys[0], vm12_cc_readys[0],
                                          vm11_cc_readys[0], vm10_cc_readys[0], vm9_cc_readys[0],  vm8_cc_readys[0],
                                          vm7_cc_readys[0],  vm6_cc_readys[0],  vm5_cc_readys[0],  vm4_cc_readys[0],
                                          vm3_cc_readys[0],  vm2_cc_readys[0],  vm1_cc_readys[0],  vm0_cc_readys[0]};
wire    [15:0]  pipe1_cc_readys = {vm15_cc_readys[1], vm14_cc_readys[1], vm13_cc_readys[1], vm12_cc_readys[1],
                                          vm11_cc_readys[1], vm10_cc_readys[1], vm9_cc_readys[1],  vm8_cc_readys[1],
                                          vm7_cc_readys[1],  vm6_cc_readys[1],  vm5_cc_readys[1],  vm4_cc_readys[1],
                                          vm3_cc_readys[1],  vm2_cc_readys[1],  vm1_cc_readys[1],  vm0_cc_readys[1]};
wire    [15:0]  pipe2_cc_readys = {vm15_cc_readys[2], vm14_cc_readys[2], vm13_cc_readys[2], vm12_cc_readys[2],
                                          vm11_cc_readys[2], vm10_cc_readys[2], vm9_cc_readys[2],  vm8_cc_readys[2],
                                          vm7_cc_readys[2],  vm6_cc_readys[2],  vm5_cc_readys[2],  vm4_cc_readys[2],
                                          vm3_cc_readys[2],  vm2_cc_readys[2],  vm1_cc_readys[2],  vm0_cc_readys[2]};
wire    [15:0]  pipe3_cc_readys = {vm15_cc_readys[3], vm14_cc_readys[3], vm13_cc_readys[3], vm12_cc_readys[3],
                                          vm11_cc_readys[3], vm10_cc_readys[3], vm9_cc_readys[3],  vm8_cc_readys[3],
                                          vm7_cc_readys[3],  vm6_cc_readys[3],  vm5_cc_readys[3],  vm4_cc_readys[3],
                                          vm3_cc_readys[3],  vm2_cc_readys[3],  vm1_cc_readys[3],  vm0_cc_readys[3]};
wire    [15:0]  pipe4_cc_readys = {vm15_cc_readys[4], vm14_cc_readys[4], vm13_cc_readys[4], vm12_cc_readys[4],
                                          vm11_cc_readys[4], vm10_cc_readys[4], vm9_cc_readys[4],  vm8_cc_readys[4],
                                          vm7_cc_readys[4],  vm6_cc_readys[4],  vm5_cc_readys[4],  vm4_cc_readys[4],
                                          vm3_cc_readys[4],  vm2_cc_readys[4],  vm1_cc_readys[4],  vm0_cc_readys[4]};
wire    [15:0]  pipe5_cc_readys = {vm15_cc_readys[5], vm14_cc_readys[5], vm13_cc_readys[5], vm12_cc_readys[5],
                                          vm11_cc_readys[5], vm10_cc_readys[5], vm9_cc_readys[5],  vm8_cc_readys[5],
                                          vm7_cc_readys[5],  vm6_cc_readys[5],  vm5_cc_readys[5],  vm4_cc_readys[5],
                                          vm3_cc_readys[5],  vm2_cc_readys[5],  vm1_cc_readys[5],  vm0_cc_readys[5]};
wire    [15:0]  pipe6_cc_readys = {vm15_cc_readys[6], vm14_cc_readys[6], vm13_cc_readys[6], vm12_cc_readys[6],
                                          vm11_cc_readys[6], vm10_cc_readys[6], vm9_cc_readys[6],  vm8_cc_readys[6],
                                          vm7_cc_readys[6],  vm6_cc_readys[6],  vm5_cc_readys[6],  vm4_cc_readys[6],
                                          vm3_cc_readys[6],  vm2_cc_readys[6],  vm1_cc_readys[6],  vm0_cc_readys[6]};
*/
wire    pap_cc_ready = 1'b1;
wire    map_cc_ready = 1'b1;
wire    mip_cc_ready = 1'b1;
wire    alu_cc_ready = 1'b1;
wire    lgc_cc_ready = 1'b1;
wire    mov_cc_ready = 1'b1;
wire    mac_cc_ready = 1'b1;

wire		slice_cc_valid;
wire		slice_cc_value;
assign slice_cc_valid =        (pap_sq_valid && pap_res_type==2'b01) |
                               (map_sq_valid && map_res_type==2'b01) |
                               (mip_sq_valid && mip_res_type==2'b01) |
                               (lgc_sq_valid && lgc_res_type==2'b01) |
                               (alu_sq_valid && alu_res_type==2'b01) |
                               (mac_sq_valid && mac_res_type==2'b01) |
                               (mov_sq_valid && mov_res_type==2'b01) ;
assign slice_cc_value =        (pap_sq_valid && pap_res_type==2'b01 && pap_res_cc) |
                               (map_sq_valid && map_res_type==2'b01 && map_res_cc) |
                               (mip_sq_valid && mip_res_type==2'b01 && mip_res_cc) |
                               (lgc_sq_valid && lgc_res_type==2'b01 && lgc_res_cc) |
                               (alu_sq_valid && alu_res_type==2'b01 && alu_res_cc) |
                               (mac_sq_valid && mac_res_type==2'b01 && mac_res_cc) |
                               (mov_sq_valid && mov_res_type==2'b01 && mov_res_cc) ;
/* yyy remove one pipe
always @(posedge clk or negedge rstn)
if(!rstn) begin
    cc_update <= 'b0;
end else begin
    cc_update  <= slice_cc_valid;
end

always @(posedge clk or negedge rstn)
if(!rstn) begin
    cc_update_value <= 'b0;
end else begin
    cc_update_value  <= slice_cc_value ;
end
*/
//-----
always @* begin
    cc_update = slice_cc_valid;
    cc_update_value = slice_cc_value;
end

//-----------------
// Merkel
/*
wire    [4+1+1+8+256-1:0]   mh_obuf_dout;
wire			mh_obuf_push;
wire			mh_obuf_pop;
wire			mh_obuf_full;
wire			mh_obuf_empty;
wire	[3:0]	mh_obuf_vm_id;
wire		mh_obuf_eop;
wire		mh_obuf_bit;
wire	[7:0]	mh_obuf_num;
wire	[255:0]	mh_obuf_data;

wire    mov_merkel_valid = mov_sq_valid && mov_res_type[1];
wire    mov_merkel_ready = !mh_obuf_full;
wire	mov_merkel_eop	 = mov_res_type == 2'b11;
assign	mh_obuf_push = mov_merkel_valid && mov_merkel_ready;
wire	mh_obuf_valid = !mh_obuf_empty;
wire	[15:0]	mov_merkel_valids = mh_obuf_valid ? (16'b1 << mh_obuf_vm_id) : 16'b0;
wire	[15:0]	mov_merkel_readys;
wire	mh_obuf_ready = mov_merkel_readys[mh_obuf_vm_id];
assign	mh_obuf_pop   = mh_obuf_valid && mh_obuf_ready;

js_vm_sfifo #(.WIDTH(4+1+1+8+256), .DEPTH(16)) u_mh_obuf (
	.clk		(clk),
	.rstn		(rstn),
	.push		(mh_obuf_push),
	.din		({mov_sq_vm_id, mov_merkel_eop, mov_res_merkel_bit, mov_res_merkel_num, mov_res_data[255:0]}),
	.pop		(mh_obuf_pop),
	.dout		(mh_obuf_dout),
	.full		(mh_obuf_full),
	.empty		(mh_obuf_empty)
);
assign	{mh_obuf_vm_id, mh_obuf_eop, mh_obuf_bit, mh_obuf_num, mh_obuf_data} = mh_obuf_dout;
wire	[1+8+256-1:0]	mh_obuf_res = {mh_obuf_bit, mh_obuf_num, mh_obuf_data};
*/

wire    [1+1+8+256-1:0]   mh_obuf_dout;
wire	mh_obuf_push;
wire	mh_obuf_pop;
wire	mh_obuf_full;
wire	mh_obuf_empty;
wire	mh_obuf_eop;
wire	mh_obuf_bit;
wire	[7:0]	mh_obuf_num	;
wire	[255:0]	mh_obuf_data;
wire	[1+8+256-1:0]	mh_obuf_res;
wire    mov_merkel_valid = mov_sq_valid && mov_res_type[1];
wire    mov_merkel_ready = !mh_obuf_full;
wire	mov_merkel_eop	 = mov_res_type == 2'b11;
assign	mh_obuf_push = mov_merkel_valid && mov_merkel_ready;
wire	mh_obuf_valid;
wire	mh_obuf_ready;


wire    mov_mh_valid;
wire    mov_mh_ready;
wire    [255:0] mov_mh_data;
wire    [3:0]   mov_mh_type;
wire    [17:0]  mov_mh_index;
wire    mov_mh_last;

wire    dbg_o_valid;
wire    dbg_o_ready;
wire    mkl_o_valid;
wire    mkl_o_ready;

js_vm_sfifo #(.WIDTH(1+1+8+256), .DEPTH(2)) u_mh_buf (
	.clk		(clk),
	.rstn		(rstn),
	.push		(mh_obuf_push),
	.din		({mov_merkel_eop, mov_res_merkel_bit, mov_res_merkel_num, mov_res_data[255:0]}),
	.pop		(mh_obuf_pop),
	.dout		(mh_obuf_dout),
	.full		(mh_obuf_full),
	.empty		(mh_obuf_empty)
);
assign {mh_obuf_eop, mh_obuf_bit, mh_obuf_num, mh_obuf_data} = mh_obuf_dout;
assign mh_obuf_valid = !mh_obuf_empty;
assign mh_obuf_pop = mh_obuf_valid & mh_obuf_ready;
assign mh_obuf_res = { mh_obuf_bit, mh_obuf_num, mh_obuf_data};

js_vm_eu_mh_loop u_mh_loop (
			     // Outputs
			     .mov_merkel_ready	(mh_obuf_ready),
			     .mov_mh_valid	(mov_mh_valid),
			     .mov_mh_data	(mov_mh_data[255:0]),
			     .mov_mh_type	(mov_mh_type[3:0]),
			     .mov_mh_index	(mov_mh_index[17:0]),
			     .mov_mh_last	(mov_mh_last),
			     // Inputs
			     .clk		(clk),
			     .rstn		(rstn),
			     .mov_merkel_valid	(mh_obuf_valid),
			     .mov_merkel_eop	(mh_obuf_eop),
			     .mov_merkel_res	(mh_obuf_res[1+8+256-1:0]),
			     .mov_mh_ready	(mov_mh_ready));

assign mov_mh_ready = mkl_o_ready && dbg_o_ready;

assign mkl_o_valid = mov_mh_valid && dbg_o_ready;
assign dbg_o_valid = mov_mh_valid && mkl_o_ready;
assign mkl_o_ready = !eu_mh_valid || eu_mh_ready;

always @(posedge clk or negedge rstn)
if(!rstn)
    eu_mh_valid  <= 1'b0;
else if(mkl_o_ready)
    eu_mh_valid  <= mkl_o_valid;

always @(posedge clk)
if(mov_mh_valid && mov_mh_ready) begin
    eu_mh_data    <= mov_mh_data;
    eu_mh_index   <= mov_mh_index;
    eu_mh_type    <= mov_mh_type;
    eu_mh_last    <= mov_mh_last;
end

//assign dbg_o_valid = mov_mh_valid && (eu_mh_ready | !eu_mh_valid);

wire    dbg_ff_push;
wire    [255:0] dbg_ff_din;
wire    [255:0] dbg_ff_dout;
wire    dbg_ff_pop;
wire    dbg_ff_full;
wire    dbg_ff_empty;

assign  dbg_ff_push = dbg_o_valid && dbg_o_ready;
wire    [2:0]   dbg_type = mov_mh_type[2:0];
wire    [255:0] dbg_data = mov_mh_data;
wire    [17:0]  dbg_index= mov_mh_index;
assign  dbg_ff_din = {dbg_type[2:0], dbg_data[252:0]};
assign  dbg_ff_pop = debug_mh_valid && debug_mh_ready;
assign  dbg_o_ready = !dbg_ff_full;

js_vm_sfifo #(.WIDTH(256), .DEPTH(2)) u_dbg_ff (
    .clk    (clk),
    .rstn   (rstn),
    .push   (dbg_ff_push),
    .din    (dbg_ff_din[255:0]),
    .pop    (dbg_ff_pop),
    .dout   (debug_mh_data),
    .full   (dbg_ff_full),
    .empty  (dbg_ff_empty)
);
assign debug_mh_valid = !dbg_ff_empty;






assign pap_sq_ready = pap_res_type == 2'b00 ? pap_gpr_ready:
                      pap_res_type == 2'b01 ? pap_cc_ready : 1'b1;
assign map_sq_ready = map_res_type == 2'b00 ? map_gpr_ready:
                      map_res_type == 2'b01 ? map_cc_ready : 1'b1;
assign mip_sq_ready = mip_res_type == 2'b00 ? mip_gpr_ready:
                      mip_res_type == 2'b01 ? mip_cc_ready : 1'b1;
assign alu_sq_ready = alu_res_type == 2'b00 ? alu_gpr_ready:
                      alu_res_type == 2'b01 ? alu_cc_ready : 1'b1;
assign lgc_sq_ready = lgc_res_type == 2'b00 ? lgc_gpr_ready:
                      lgc_res_type == 2'b01 ? lgc_cc_ready : 1'b1;
assign mac_sq_ready = mac_res_type == 2'b00 ? mac_gpr_ready:
                      mac_res_type == 2'b01 ? mac_cc_ready : 1'b1;

assign mov_sq_ready = mov_res_type == 2'b00 ? mov_gpr_ready:
                      mov_res_type == 2'b01 ? mov_cc_ready : mov_merkel_ready;
//                      mov_res_type == 2'b01 ? mov_cc_ready : 1'b1;

// func definition


function [1+8-1:0]    extract_merkel;
input   [ISA_BITS+1+REG_WIDTH-1:0]    res;
reg [ISA_BITS-1:0]  isa;
reg cc_value;
reg [REG_WIDTH-1:0] dst_data;
reg [GPR_ADDR_BITS-1:0] dst_addr;
reg [1:0]   dst_type;
reg [2:0]   opcode;
reg [7:0]   imm0;
reg [7:0]   num;
reg is_bit;
begin
    {isa, cc_value, dst_data} = res;
    dst_type = isa[78:77];
    dst_addr = isa[66:57];
    imm0     = isa[33:26];
    opcode   = isa[5:3];
    is_bit   = opcode == 3'h3;
    num      = opcode == 3'h3 ? imm0 : 
               opcode == 3'h2 ? 8'h1 : 8'h0;
    extract_merkel = {is_bit, num};
end
endfunction

function [ISA_DST_FMT_BITS+ISA_OPCODE_BITS+2+1+GPR_ADDR_BITS+REG_WIDTH-1:0]    extract_one_dst;
input   [ISA_BITS+1+REG_WIDTH-1:0]    res;
reg [ISA_BITS-1:0]  isa;
reg cc_value;
reg [REG_WIDTH-1:0] dst_data;
reg [GPR_ADDR_BITS-1:0] dst_addr;
reg [ISA_OPCODE_BITS-1:0]   opcode;
reg [ISA_DST_FMT_BITS-1:0]  dst_fmt;
reg [1:0]   dst_type;
begin
    {isa, cc_value, dst_data} = res;
    dst_fmt  = isa[82:79];
    dst_type = isa[78:77];
    dst_addr = isa[66:57];
    opcode   = isa[5:3];
    extract_one_dst = {dst_fmt, dst_type, opcode, cc_value, dst_addr, dst_data};
end
endfunction

function [2+1+2*GPR_ADDR_BITS+2*REG_WIDTH-1:0]    extract_two_dst;
input   [ISA_BITS+1+2*REG_WIDTH-1:0]    res;
reg [ISA_BITS-1:0]  isa;
reg cc_value;
reg [REG_WIDTH-1:0] dst0_data;
reg [GPR_ADDR_BITS-1:0] dst0_addr;
reg [REG_WIDTH-1:0] dst1_data;
reg [GPR_ADDR_BITS-1:0] dst1_addr;
reg [1:0]   dst_type;
begin
    {isa, cc_value, dst1_data, dst0_data} = res;
    dst_type = isa[78:77];
    dst0_addr = isa[66:57];
    dst1_addr = isa[76:67];
    extract_two_dst = {dst_type, cc_value, dst1_addr, dst1_data, dst0_addr, dst0_data};
end

endfunction









endmodule
// Verilog-mode Setting:
// Local Variables:
// verilog-library-directories: ("../sq/" "./" "../eu/")
// verilog-auto-inst-param-value: t
// End:



