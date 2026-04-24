module js_vm_macro_top
    (/*AUTOARG*/
   // Outputs
   mac_active, sq_mac_ready, mac_sq_res, mac_sq_valid, mac_sq_vm_id,
   mac_sq_mask, mac_sq_fc_dec, mac_sq_fc_dec_vm_id,
   // Inputs
   clk, rstn, sq_mac_valid, sq_mac_data, sq_mac_vm_id, mac_sq_ready
   );
    `include "js_vm.vh"
    input clk;
    input rstn;
    output  mac_active;
    input sq_mac_valid;
    input [ISA_BITS+2*REG_WIDTH+1-1:0] sq_mac_data;
    input [3:0]                        sq_mac_vm_id;
    output                             sq_mac_ready;


    output[ISA_BITS+2*REG_WIDTH+1-1:0] mac_sq_res;
    output                             mac_sq_valid;
    output  [3:0]                      mac_sq_vm_id;
    output  [1:0]                      mac_sq_mask;
    input                              mac_sq_ready;

    output  logic   [FC_NUM-1:0]              mac_sq_fc_dec;
    output  logic   [3:0]              mac_sq_fc_dec_vm_id;
    
    logic leq_is_valid;
    logic ternary_is_valid;
    logic xor_is_valid;
    logic and_is_valid;
    logic or_is_valid;
    logic lessthan_is_valid;
    logic [2:0] opcode;
    logic [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_leq_data;
    logic                               eu_macro_leq_i_valid;
    logic [3:0]                         eu_macro_leq_i_vm_id;
    logic                               eu_macro_leq_o_ready;
    logic                               eu_macro_leq_o_valid;
    logic                               eu_macro_leq_i_ready;
    logic [3:0]                         eu_macro_leq_o_vm_id;
    logic [ISA_BITS+REG_WIDTH:0]        eu_macro_leq_variable;
    logic [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_ternary_data;
    logic                               eu_macro_ternary_i_valid;
    logic [3:0]                         eu_macro_ternary_i_vm_id;
    logic                               eu_macro_ternary_o_ready;
    logic                               eu_macro_ternary_o_valid;
    logic                               eu_macro_ternary_i_ready;
    logic [3:0]                         eu_macro_ternary_o_vm_id;
    logic [ISA_BITS+REG_WIDTH:0]        eu_macro_ternary_variable;
    logic [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_xor_data;
    logic                               eu_macro_xor_i_valid;
    logic [3:0]                         eu_macro_xor_i_vm_id;
    logic                               eu_macro_xor_o_ready;
    logic                               eu_macro_xor_o_valid;
    logic                               eu_macro_xor_i_ready;
    logic [3:0]                         eu_macro_xor_o_vm_id;
    logic [ISA_BITS+REG_WIDTH:0]        eu_macro_xor_variable;
    logic [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_and_data;
    logic                               eu_macro_and_i_valid;
    logic [3:0]                         eu_macro_and_i_vm_id;
    logic                               eu_macro_and_o_ready;
    logic                               eu_macro_and_i_ready;
    logic                               eu_macro_and_o_valid;
    logic [3:0]                         eu_macro_and_o_vm_id;
    logic [ISA_BITS+REG_WIDTH+1-1:0]    eu_macro_and_res;
    logic [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_or_data;
    logic                               eu_macro_or_i_valid;
    logic [3:0]                         eu_macro_or_i_vm_id;
    logic                               eu_macro_or_o_ready;
    logic                               eu_macro_or_i_ready;
    logic                               eu_macro_or_o_valid;
    logic [3:0]                         eu_macro_or_o_vm_id;
    logic [ISA_BITS+REG_WIDTH+1-1:0]    eu_macro_or_res;    
    logic [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_lessthan_data;
    logic                               eu_macro_lessthan_i_valid;
    logic [3:0]                         eu_macro_lessthan_i_vm_id;
    logic                               eu_macro_lessthan_o_ready;
    logic                               eu_macro_lessthan_i_ready;
    logic                               eu_macro_lessthan_o_valid;
    logic [3:0]                         eu_macro_lessthan_o_vm_id;
    logic [1:0]                         eu_macro_lessthan_o_mask;
    logic [ISA_BITS+2*REG_WIDTH+1-1:0]  eu_macro_lessthan_res;
    logic [5:0]                         eu_macro_valids;
    logic [5:0]                         eu_macro_readys;
    //logic                               rr_arb_o_valid;
    //logic                               rr_arb_o_ready;
    //logic [2:0]                         rr_arb_grant_id;


   wire [2:0] 				sync_din;
   wire [2:0] 				sync_dout;
   wire 				sync_pop;
   wire 				sync_full;
   wire 				sync_empty;
   wire 				sync_push = sq_mac_valid && sq_mac_ready;
    
    assign opcode           = sq_mac_data[2*REG_WIDTH+1+3+:3];
    assign leq_is_valid     = sq_mac_valid && !sync_full && opcode==OPCODE_MCLEQ    ;
    assign ternary_is_valid = sq_mac_valid && !sync_full && opcode==OPCODE_MCTERNARY;
    assign xor_is_valid     = sq_mac_valid && !sync_full && opcode==OPCODE_MCXOR    ;
    assign and_is_valid     = sq_mac_valid && !sync_full && opcode==OPCODE_MCAND    ;
    assign or_is_valid      = sq_mac_valid && !sync_full && opcode==OPCODE_MCOR     ;
    assign lessthan_is_valid= sq_mac_valid && !sync_full && opcode==OPCODE_MCLT     ;
    assign sq_mac_ready     = opcode==OPCODE_MCLEQ     ?    eu_macro_leq_i_ready && !sync_full :
                              opcode==OPCODE_MCTERNARY ?    eu_macro_ternary_i_ready && !sync_full :
                              opcode==OPCODE_MCXOR     ?    eu_macro_xor_i_ready && !sync_full:
                              opcode==OPCODE_MCAND     ?    eu_macro_and_i_ready && !sync_full :
                              opcode==OPCODE_MCOR      ?    eu_macro_or_i_ready && !sync_full:
                              opcode==OPCODE_MCLT      ?    eu_macro_lessthan_i_ready && !sync_full : 0;
    assign eu_macro_leq_data      = sq_mac_data;
    assign eu_macro_ternary_data  = sq_mac_data;
    assign eu_macro_xor_data      = sq_mac_data;
    assign eu_macro_and_data      = sq_mac_data;
    assign eu_macro_or_data       = sq_mac_data;
    assign eu_macro_lessthan_data = sq_mac_data;
    assign eu_macro_leq_i_vm_id      = sq_mac_vm_id;
    assign eu_macro_ternary_i_vm_id  = sq_mac_vm_id;
    assign eu_macro_xor_i_vm_id      = sq_mac_vm_id;
    assign eu_macro_and_i_vm_id      = sq_mac_vm_id;
    assign eu_macro_or_i_vm_id       = sq_mac_vm_id;
    assign eu_macro_lessthan_i_vm_id = sq_mac_vm_id;
    assign eu_macro_leq_i_valid      = leq_is_valid     ;
    assign eu_macro_ternary_i_valid  = ternary_is_valid ;
    assign eu_macro_xor_i_valid      = xor_is_valid     ;
    assign eu_macro_and_i_valid      = and_is_valid     ;
    assign eu_macro_or_i_valid       = or_is_valid      ;
    assign eu_macro_lessthan_i_valid = lessthan_is_valid;
   // assign eu_macro_valids           = {eu_macro_leq_o_valid, eu_macro_ternary_o_valid, eu_macro_xor_o_valid, eu_macro_and_o_valid, eu_macro_or_o_valid, eu_macro_lessthan_o_valid};
   //  assign {eu_macro_leq_o_ready, eu_macro_ternary_o_ready, eu_macro_xor_o_ready, eu_macro_and_o_ready, eu_macro_or_o_ready, eu_macro_lessthan_o_ready} = eu_macro_readys;
   //  assign mac_sq_valid              = rr_arb_o_valid;
   //  assign rr_arb_o_ready            = mac_sq_ready;
   //  assign mac_sq_vm_id              = rr_arb_grant_id == 3'h5 ? eu_macro_leq_o_vm_id :
   //                                     rr_arb_grant_id == 3'h4 ? eu_macro_ternary_o_vm_id :
   //                                     rr_arb_grant_id == 3'h3 ? eu_macro_xor_o_vm_id :
   //                                     rr_arb_grant_id == 3'h2 ? eu_macro_and_o_vm_id :
   //                                     rr_arb_grant_id == 3'h1 ? eu_macro_or_o_vm_id :
   //                                     rr_arb_grant_id == 3'h0 ? eu_macro_lessthan_o_vm_id : 0;
   //   assign mac_sq_res                = rr_arb_grant_id == 3'h5 ? {eu_macro_leq_variable[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1] ,{REG_WIDTH{1'b0}}, eu_macro_leq_variable[REG_WIDTH-1:0]}:                                          
   //                                      rr_arb_grant_id == 3'h4 ? {eu_macro_ternary_variable[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_ternary_variable[REG_WIDTH-1:0]} :
   //                                      rr_arb_grant_id == 3'h3 ? {eu_macro_xor_variable[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_xor_variable[REG_WIDTH-1:0]} :
   //                                      rr_arb_grant_id == 3'h2 ? {eu_macro_and_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_and_res[REG_WIDTH-1:0]} :
   //                                      rr_arb_grant_id == 3'h1 ? {eu_macro_or_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_or_res[REG_WIDTH-1:0]} :
   //                                      rr_arb_grant_id == 3'h0 ? eu_macro_lessthan_res : 0;
   assign mac_sq_mask               = mac_sq_res[2*REG_WIDTH+1+3+:3]== OPCODE_MCLT? eu_macro_lessthan_o_mask : 2'b01;

wire    [FC_NUM-1:0]    sf = get_sf(mac_sq_res[ISA_BITS+2*REG_WIDTH+1-1-:ISA_BITS]);      
    wire    [FC_NUM-1:0] fc_dec             = sf & {FC_NUM{mac_sq_valid & mac_sq_ready}};
/*    
always @(posedge clk or negedge rstn)
if(!rstn) begin
    mac_sq_fc_dec   <= 2'b00;
    mac_sq_fc_dec_vm_id <= 4'b0;
end else begin
    mac_sq_fc_dec   <= fc_dec;
    mac_sq_fc_dec_vm_id <= mac_sq_vm_id;
end
*/
always @* begin
    mac_sq_fc_dec   = fc_dec;
    mac_sq_fc_dec_vm_id = mac_sq_vm_id;
end


/* -----\/----- EXCLUDED -----\/-----
    js_vm_rr_arb #(.NUM(6), .ID_BITS(3)) u_macro_rr_arb (
        .clk      (clk), 
        .rstn     (rstn), 
        .in_valids(eu_macro_valids), 
        .in_readys(eu_macro_readys),
        .out_valid(rr_arb_o_valid), 
        .out_ready(rr_arb_o_ready), 
        .grant_id (rr_arb_grant_id)
    );
 -----/\----- EXCLUDED -----/\----- */



   assign sync_pop = mac_sq_valid && mac_sq_ready; 

   assign sync_din = opcode==OPCODE_MCLEQ     ?    3'b000 :
                     opcode==OPCODE_MCTERNARY ?    3'b001:
                     opcode==OPCODE_MCXOR     ?    3'b010:
                     opcode==OPCODE_MCAND     ?    3'b011 :
                     opcode==OPCODE_MCOR      ?    3'b100:
                     opcode==OPCODE_MCLT      ?    3'b101 : 3'b000;
   

   js_vm_sfifo #(.WIDTH(3), .DEPTH(2)) u_sync_fifo (
    .clk        (clk),
    .rstn       (rstn),
    .push       (sync_push),
    .din        (sync_din),
    .pop        (sync_pop),
    .dout       (sync_dout),
    .empty      (sync_empty),
    .full       (sync_full)
);
wire    merge_o_valid = !sync_empty && ((sync_dout==3'b000 && eu_macro_leq_o_valid) || (sync_dout==3'b001 && eu_macro_ternary_o_valid) 
					  || (sync_dout==3'b010 && eu_macro_xor_o_valid) || (sync_dout==3'b011 && eu_macro_and_o_valid)
					  || (sync_dout == 3'b100 && eu_macro_or_o_valid) || (sync_dout == 3'b101 && eu_macro_lessthan_o_valid)
					  );
wire    [3:0]   merge_o_vm_id = sync_dout==3'b000 ? eu_macro_leq_o_vm_id :
			  sync_dout==3'b001 ? eu_macro_ternary_o_vm_id :
			  sync_dout==3'b010 ? eu_macro_xor_o_vm_id : 
			  sync_dout == 3'b011 ? eu_macro_and_o_vm_id :
			  sync_dout == 3'b100 ? eu_macro_or_o_vm_id :
			  sync_dout == 3'b101 ? eu_macro_lessthan_o_valid :  4'b0;
wire    [ISA_BITS+2*REG_WIDTH+1-1:0]    merge_o_res = sync_dout==3'b000 ? {eu_macro_leq_variable[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1] ,{REG_WIDTH{1'b0}}, eu_macro_leq_variable[REG_WIDTH-1:0]}:
			  sync_dout==3'b001 ? {eu_macro_ternary_variable[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_ternary_variable[REG_WIDTH-1:0]}:
			  sync_dout==3'b010 ?  {eu_macro_xor_variable[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_xor_variable[REG_WIDTH-1:0]}: 
			  sync_dout == 3'b011 ?  {eu_macro_and_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_and_res[REG_WIDTH-1:0]}:
			  sync_dout == 3'b100 ?  {eu_macro_or_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_or_res[REG_WIDTH-1:0]}:
			  sync_dout == 3'b101 ? eu_macro_lessthan_res :  0;
wire    merge_o_ready;

wire    obuf_push;
wire    [4+ISA_BITS+2*REG_WIDTH+1-1:0]    obuf_din; 
wire    obuf_pop;      
wire    [4+ISA_BITS+2*REG_WIDTH+1-1:0]    obuf_dout; 
wire    obuf_empty;
wire    obuf_full;
assign    obuf_push = merge_o_valid && merge_o_ready;
assign    obuf_din  = {merge_o_vm_id, merge_o_res};
assign    mac_sq_valid = !obuf_empty;
assign    {mac_sq_vm_id, mac_sq_res} = obuf_dout;
assign    obuf_pop = mac_sq_valid && mac_sq_ready;

assign  merge_o_ready = !obuf_full;

js_vm_sfifo #(.WIDTH(4+ISA_BITS+2*REG_WIDTH+1), .DEPTH(2)) u_out_fifo (
    .clk        (clk),
    .rstn       (rstn),
    .push       (obuf_push),
    .din        (obuf_din),
    .pop        (obuf_pop),
    .dout       (obuf_dout),
    .empty      (obuf_empty),
    .full       (obuf_full)
);
/*
   assign  mac_sq_valid = !sync_empty && ((sync_dout==3'b000 && eu_macro_leq_o_valid) || (sync_dout==3'b001 && eu_macro_ternary_o_valid) 
					  || (sync_dout==3'b010 && eu_macro_xor_o_valid) || (sync_dout==3'b011 && eu_macro_and_o_valid)
					  || (sync_dout == 3'b100 && eu_macro_or_o_valid) || (sync_dout == 3'b101 && eu_macro_lessthan_o_valid)
					  );
   assign  mac_sq_vm_id = sync_dout==3'b000 ? eu_macro_leq_o_vm_id :
			  sync_dout==3'b001 ? eu_macro_ternary_o_vm_id :
			  sync_dout==3'b010 ? eu_macro_xor_o_vm_id : 
			  sync_dout == 3'b011 ? eu_macro_and_o_vm_id :
			  sync_dout == 3'b100 ? eu_macro_or_o_vm_id :
			  sync_dout == 3'b101 ? eu_macro_lessthan_o_valid :  4'b0;
   assign  mac_sq_res   = sync_dout==3'b000 ? {eu_macro_leq_variable[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1] ,{REG_WIDTH{1'b0}}, eu_macro_leq_variable[REG_WIDTH-1:0]}:
			  sync_dout==3'b001 ? {eu_macro_ternary_variable[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_ternary_variable[REG_WIDTH-1:0]}:
			  sync_dout==3'b010 ?  {eu_macro_xor_variable[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_xor_variable[REG_WIDTH-1:0]}: 
			  sync_dout == 3'b011 ?  {eu_macro_and_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_and_res[REG_WIDTH-1:0]}:
			  sync_dout == 3'b100 ?  {eu_macro_or_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS+1],{REG_WIDTH{1'b0}}, eu_macro_or_res[REG_WIDTH-1:0]}:
			  sync_dout == 3'b101 ? eu_macro_lessthan_res :  0;
*/
//   assign  eu_macro_leq_o_ready = !sync_empty && sync_dout==3'b000 && mac_sq_ready;
//   assign  eu_macro_ternary_o_ready = !sync_empty && sync_dout==3'b001 && mac_sq_ready;
//   assign  eu_macro_xor_o_ready = !sync_empty && sync_dout==3'b010 && mac_sq_ready;
//   assign  eu_macro_and_o_ready = !sync_empty && sync_dout==3'b011 && mac_sq_ready;
//   assign  eu_macro_or_o_ready = !sync_empty && sync_dout==3'b100 && mac_sq_ready;
//   assign  eu_macro_lessthan_o_ready = !sync_empty && sync_dout==3'b101 && mac_sq_ready;
   
   assign  eu_macro_leq_o_ready = !sync_empty && sync_dout==3'b000 && merge_o_ready;
   assign  eu_macro_ternary_o_ready = !sync_empty && sync_dout==3'b001 && merge_o_ready;
   assign  eu_macro_xor_o_ready = !sync_empty && sync_dout==3'b010 && merge_o_ready;
   assign  eu_macro_and_o_ready = !sync_empty && sync_dout==3'b011 && merge_o_ready;
   assign  eu_macro_or_o_ready = !sync_empty && sync_dout==3'b100 && merge_o_ready;
   assign  eu_macro_lessthan_o_ready = !sync_empty && sync_dout==3'b101 && merge_o_ready;
   
    js_vm_macro_leq u_macro_leq(
        .clk                  (clk                  ),
        .rstn                 (rstn                 ),
        .eu_macro_leq_data    (eu_macro_leq_data    ),
        .eu_macro_leq_i_valid (eu_macro_leq_i_valid ),
        .eu_macro_leq_i_vm_id (eu_macro_leq_i_vm_id ),
        .eu_macro_leq_o_ready (eu_macro_leq_o_ready ),
        .eu_macro_leq_o_valid (eu_macro_leq_o_valid ),
        .eu_macro_leq_i_ready (eu_macro_leq_i_ready ),
        .eu_macro_leq_o_vm_id (eu_macro_leq_o_vm_id ),
        .eu_macro_leq_variable(eu_macro_leq_variable)
    );
    js_vm_macro_ternary u_macro_ternary(
        .clk                      (clk                      ),
        .rstn                     (rstn                     ),
        .eu_macro_ternary_data    (eu_macro_ternary_data    ),
        .eu_macro_ternary_i_valid (eu_macro_ternary_i_valid ),
        .eu_macro_ternary_i_vm_id (eu_macro_ternary_i_vm_id ),
        .eu_macro_ternary_o_ready (eu_macro_ternary_o_ready ),
        .eu_macro_ternary_o_valid (eu_macro_ternary_o_valid ),
        .eu_macro_ternary_i_ready (eu_macro_ternary_i_ready ),
        .eu_macro_ternary_o_vm_id (eu_macro_ternary_o_vm_id ),
        .eu_macro_ternary_variable(eu_macro_ternary_variable)
    );    
    js_vm_macro_xor u_macro_xor (
        .clk                  (clk                  ),
        .rstn                 (rstn                 ),
        .eu_macro_xor_data    (eu_macro_xor_data    ),
        .eu_macro_xor_i_valid (eu_macro_xor_i_valid ),
        .eu_macro_xor_i_vm_id (eu_macro_xor_i_vm_id ),
        .eu_macro_xor_o_ready (eu_macro_xor_o_ready ),
        .eu_macro_xor_o_valid (eu_macro_xor_o_valid ),
        .eu_macro_xor_i_ready (eu_macro_xor_i_ready ),
        .eu_macro_xor_o_vm_id (eu_macro_xor_o_vm_id ),
        .eu_macro_xor_variable(eu_macro_xor_variable)
    );
    js_vm_macro_and u_macro_and (
        .clk                 (clk                 ),
        .rstn                (rstn                ),
        .eu_macro_and_data   (eu_macro_and_data   ),
        .eu_macro_and_i_valid(eu_macro_and_i_valid),
        .eu_macro_and_i_vm_id(eu_macro_and_i_vm_id),
        .eu_macro_and_o_ready(eu_macro_and_o_ready),
        .eu_macro_and_i_ready(eu_macro_and_i_ready),
        .eu_macro_and_o_valid(eu_macro_and_o_valid),
        .eu_macro_and_o_vm_id(eu_macro_and_o_vm_id),
        .eu_macro_and_res    (eu_macro_and_res    )
    );
    js_vm_macro_or u_macro_or (
        .clk                 (clk                ),
        .rstn                (rstn               ),
        .eu_macro_or_data    (eu_macro_or_data   ),
        .eu_macro_or_i_valid (eu_macro_or_i_valid),
        .eu_macro_or_i_vm_id (eu_macro_or_i_vm_id),
        .eu_macro_or_o_ready (eu_macro_or_o_ready),
        .eu_macro_or_i_ready (eu_macro_or_i_ready),
        .eu_macro_or_o_valid (eu_macro_or_o_valid),
        .eu_macro_or_o_vm_id (eu_macro_or_o_vm_id),
        .eu_macro_or_res     (eu_macro_or_res    )
    );
    js_vm_macro_lessthan u_macro_lessthan (
        .clk                      (clk                      ),
        .rstn                     (rstn                     ),
        .eu_macro_lessthan_data   (eu_macro_lessthan_data   ),
        .eu_macro_lessthan_i_valid(eu_macro_lessthan_i_valid),
        .eu_macro_lessthan_i_vm_id(eu_macro_lessthan_i_vm_id),
        .eu_macro_lessthan_o_ready(eu_macro_lessthan_o_ready),
        .eu_macro_lessthan_i_ready(eu_macro_lessthan_i_ready),
        .eu_macro_lessthan_o_valid(eu_macro_lessthan_o_valid),
        .eu_macro_lessthan_o_vm_id(eu_macro_lessthan_o_vm_id),
        .eu_macro_lessthan_o_mask (eu_macro_lessthan_o_mask ),
        .eu_macro_lessthan_res    (eu_macro_lessthan_res    )
    );    

assign mac_active = !sync_empty || !obuf_empty || sq_mac_valid;

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
