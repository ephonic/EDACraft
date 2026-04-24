module js_vm_map_top
    (/*AUTOARG*/
   // Outputs
   map_active, sq_map_ready, map_sq_fc_dec, map_sq_fc_dec_vm_id,
   map_sq_res, map_sq_valid, map_sq_vm_id,
   // Inputs
   clk, rstn, sq_map_valid, sq_map_data, sq_map_modsub_q,
   sq_map_modadd_q, sq_map_vm_id, map_sq_ready
   );

    `include "js_vm.vh"
    input clk;
    input rstn;
    output  map_active;
    input sq_map_valid;
    input [ISA_BITS+2*REG_WIDTH+1-1:0] sq_map_data;
    input [DATA_WIDTH-1:0]             sq_map_modsub_q;
    input [DATA_WIDTH-1:0]             sq_map_modadd_q;
    input [3:0]                        sq_map_vm_id;
    output                             sq_map_ready;

    output  logic   [FC_NUM-1:0]              map_sq_fc_dec;
    output  logic   [3:0]              map_sq_fc_dec_vm_id;

    output[ISA_BITS+REG_WIDTH+1-1:0]   map_sq_res;
    output                             map_sq_valid;
    output  [3:0]                      map_sq_vm_id;
    input                              map_sq_ready;



    logic                              modsub_i_valid;
    logic                              modsub_o_ready;
    logic  [3:0]                       modsub_o_vm_id;
    logic                              modsub_o_valid;
    logic                              modsub_i_ready;
    logic  [ISA_BITS+REG_WIDTH+1-1:0]  modsub_res;
    logic                              modadd_i_valid;
    logic                              modadd_o_ready;
    logic  [3:0]                       modadd_o_vm_id;
    logic                              modadd_o_valid;
    logic                              modadd_i_ready;
    logic  [ISA_BITS+REG_WIDTH+1-1:0]  modadd_res;
    logic                              modacc_i_valid;
    logic                              modacc_o_ready;
    logic  [3:0]                       modacc_o_vm_id;
    logic                              modacc_o_valid;
    logic                              modacc_i_ready;
    logic  [ISA_BITS+REG_WIDTH+1-1:0]  modacc_res;

wire    sync_push = sq_map_valid && sq_map_ready;
wire    [1:0]   sync_din;
wire    sync_pop;      
wire    [1:0]   sync_dout;         // used to control if modmul result is sent to acc
wire    sync_empty;
wire    sync_full;
js_vm_sfifo #(.WIDTH(2), .DEPTH(16)) u_sync_fifo (
    .clk        (clk),
    .rstn       (rstn),
    .push       (sync_push),
    .din        (sync_din),
    .pop        (sync_pop),
    .dout       (sync_dout),
    .empty      (sync_empty),
    .full       (sync_full)
);

assign sync_pop = map_sq_valid && map_sq_ready;

    logic [1:0]                        rr_arb_valids;
    logic [1:0]                        rr_arb_readys;
    logic                              rr_arb_o_valid;
    logic                              rr_arb_o_ready;
    logic                              rr_arb_grant_id;
    logic [ISA_OPTYPE_BITS-1:0]         optype;
    logic [ISA_OPCODE_BITS-1:0]         opcode;
    logic [ISA_CC_BITS-1:0]             cc_reg;
    logic [ISA_SF_BITS-1:0]             sf;
    logic [ISA_WF_BITS-1:0]             wf;
    logic [ISA_SRC0_REG_BITS-1:0]       src0_reg;
    logic [ISA_SRC0_TYPE_BITS-1:0]      src0_type;
    logic [ISA_SRC0_FMT_BITS-1:0]       src0_fmt;
    logic [ISA_SRC0_IMM_BITS-1:0]       src0_imm;
    logic [ISA_SRC1_REG_BITS-1:0]       src1_reg;
    logic [ISA_SRC1_TYPE_BITS-1:0]      src1_type;
    logic [ISA_SRC1_FMT_BITS-1:0]       src1_fmt;
    logic [ISA_SRC1_IMM_BITS-1:0]       src1_imm;
    logic [ISA_DST0_REG_BITS-1:0]       dst0_reg;
    logic [ISA_DST1_REG_BITS-1:0]       dst1_reg;
    logic [ISA_DST_TYPE_BITS-1:0]       dst_type;
    logic [ISA_DST_FMT_BITS-1:0]        dst_fmt;
    logic [ISA_RSV_BITS-1:0]            rsv;    
    logic                               cc_value;
    logic [REG_WIDTH-1:0]               src1_value;
    logic [REG_WIDTH-1:0]               src0_value;    
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
        optype,
        cc_value,
        src1_value,
        src0_value
        } = sq_map_data;
    logic    src0_tmp [REG_WIDTH-1:0];
    logic    src1_tmp [REG_WIDTH-1:0];
    logic    src0_truncated_bit;
    logic    src1_truncated_bit;
    logic    [2*REG_WIDTH+ISA_BITS+1-1:0] pipe_used_data;
    genvar i;
    generate
        for (i=0; i<REG_WIDTH; i=i+1) begin: ASSIGN_SRC0
            if ((i>=0) & (i<DATA_WIDTH)) begin
                assign src0_tmp[i] = src0_value[i];
                assign src1_tmp[i] = src1_value[i];
            end
            else begin
                assign src0_tmp[i] = 1'b0;
                assign src1_tmp[i] = 1'b0;
            end
        end
    endgenerate      
assign	sync_din  = opcode==OPCODE_MADD_ACC ? 2'b00 :
                    opcode==OPCODE_MSUB ? 2'b01 :
                    opcode==OPCODE_MADD ? 2'b10 : 2'b00;   // 2'b00: MODADD_ACC, 2'b01: MODSUB, 2'b10: MODADD  
    assign src0_truncated_bit = src0_tmp[src0_imm];
    assign src1_truncated_bit = src1_tmp[src1_imm];
    assign pipe_used_data     = {sq_map_data[2*REG_WIDTH+:ISA_BITS+1], src1_fmt==4'ha ? {{(REG_WIDTH-1){1'b0}}, src1_truncated_bit}: src1_value, src0_fmt==4'ha ? {{(REG_WIDTH-1){1'b0}}, src0_truncated_bit}: src0_value};

    assign modsub_i_valid   = sq_map_valid && !sync_full && opcode==OPCODE_MSUB    ;
    assign modadd_i_valid   = sq_map_valid && !sync_full && opcode==OPCODE_MADD    ;
    assign modacc_i_valid   = sq_map_valid && !sync_full && opcode==OPCODE_MADD_ACC    ;
    assign sq_map_ready     = opcode==OPCODE_MSUB ? modsub_i_ready && !sync_full :
                              opcode==OPCODE_MADD ? modadd_i_ready && !sync_full: 
                              opcode==OPCODE_MADD_ACC ? modacc_i_ready && !sync_full : 0;

//    assign {modadd_o_ready, modsub_o_ready} = rr_arb_readys;
//    assign rr_arb_valids                    = {modadd_o_valid, modsub_o_valid};
//    assign map_sq_valid                     = rr_arb_o_valid;
//    assign rr_arb_o_ready                   = map_sq_ready;
//    assign map_sq_vm_id                     = rr_arb_grant_id ? modadd_o_vm_id : modsub_o_vm_id;
//    assign map_sq_res                       = rr_arb_grant_id ? modadd_res     : modsub_res;

assign  map_sq_valid = !sync_empty && ((sync_dout==2'b00 && modacc_o_valid) || (sync_dout==2'b01 && modsub_o_valid) || (sync_dout==2'b10 && modadd_o_valid));
assign  map_sq_vm_id = sync_dout==2'b00 ? modacc_o_vm_id :
                       sync_dout==2'b01 ? modsub_o_vm_id :
                       sync_dout==2'b10 ? modadd_o_vm_id : 4'b0;
assign  map_sq_res   = sync_dout==2'b00 ? modacc_res :
                       sync_dout==2'b01 ? modsub_res :
                       sync_dout==2'b10 ? modadd_res : 'b0;
assign  modacc_o_ready = !sync_empty && sync_dout==2'b00 && map_sq_ready;
assign  modsub_o_ready = !sync_empty && sync_dout==2'b01 && map_sq_ready;
assign  modadd_o_ready = !sync_empty && sync_dout==2'b10 && map_sq_ready;


wire    [FC_NUM-1:0]    map_sq_sf = get_sf(map_sq_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS]);
    wire    [FC_NUM-1:0]   fc_dec = {FC_NUM{(map_sq_valid & map_sq_ready)}} & map_sq_sf;
    /*
    always @(posedge clk or negedge rstn)
    if(!rstn) begin
        map_sq_fc_dec   <= 2'b00;
        map_sq_fc_dec_vm_id <= 4'b0;

    end else begin
        map_sq_fc_dec   <= fc_dec;
        map_sq_fc_dec_vm_id <= modsub_o_valid ? modsub_o_vm_id : modadd_o_vm_id;
    end
*/
always @* begin
        map_sq_fc_dec   = fc_dec;
        map_sq_fc_dec_vm_id = modsub_o_valid ? modsub_o_vm_id : modadd_o_vm_id;
end
/*
//    assign map_sq_fc_dec_vm_id = modsub_o_valid ? modsub_o_vm_id : modadd_o_vm_id;
//    assign map_sq_fc_dec       = map_sq_res[2*REG_WIDTH+1+7+:2];
    js_vm_rr_arb #(.NUM(2), .ID_BITS(1)) u_map_rr_arb (
        .clk      (clk), 
        .rstn     (rstn), 
        .in_valids(rr_arb_valids), 
        .in_readys(rr_arb_readys),
        .out_valid(rr_arb_o_valid), 
        .out_ready(rr_arb_o_ready), 
        .grant_id (rr_arb_grant_id)
    );
    */
    js_vm_modsub u_modsub
        (
            .clk    (clk),
            .rstn   (rstn),
            .data   (pipe_used_data),
            .q      (sq_map_modsub_q),
            .res    (modsub_res),
            .i_vm_id(sq_map_vm_id),
            .o_vm_id(modsub_o_vm_id),
            .i_valid(modsub_i_valid),
            .o_valid(modsub_o_valid),
            .i_ready(modsub_i_ready),
            .o_ready(modsub_o_ready)
        );
    js_vm_modaddc u_modacc
        (
            .clk    (clk),
            .rstn   (rstn),
            .data   (pipe_used_data),
            .q      (sq_map_modadd_q),
            .res    (modacc_res),
            .i_vm_id(sq_map_vm_id),
            .o_vm_id(modacc_o_vm_id),
            .i_valid(modacc_i_valid),
            .o_valid(modacc_o_valid),
            .i_ready(modacc_i_ready),
            .o_ready(modacc_o_ready)
        );
    js_vm_modadd u_modadd
        (
            .clk    (clk),
            .rstn   (rstn),
            .data   (pipe_used_data),
            .q      (sq_map_modadd_q),
            .res    (modadd_res),
            .i_vm_id(sq_map_vm_id),
            .o_vm_id(modadd_o_vm_id),
            .i_valid(modadd_i_valid),
            .o_valid(modadd_o_valid),
            .i_ready(modadd_i_ready),
            .o_ready(modadd_o_ready)
        );

assign map_active = !sync_empty || sq_map_valid;


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

