module js_vm_pap_top
(/*AUTOARG*/
   // Outputs
   pap_active, sq_pap_ready, pap_sq_fc_dec, pap_sq_fc_dec_vm_id,
   pap_sq_valid, pap_sq_res, pap_sq_vm_id, pap_sq_hq_rel_valid,
   pap_sq_hq_rel_vm_id,
   // Inputs
   clk, rstn, sq_pap_valid, sq_pap_data, sq_pap_q, sq_pap_mu,
   sq_pap_vm_id, pap_sq_ready
   );

    `include "js_vm.vh"
    localparam MODMUL_DELAY = 18;
    input clk;
    input rstn;
    output  pap_active;
    input sq_pap_valid;
    input [ISA_BITS+2*REG_WIDTH+1-1:0] sq_pap_data;
    input [255:0]                      sq_pap_q;
    input [255:0]                      sq_pap_mu;
    input [3:0]                        sq_pap_vm_id;
    output  logic                      sq_pap_ready;
    output  logic   [FC_NUM-1:0]       pap_sq_fc_dec;
    output  logic   [3:0]              pap_sq_fc_dec_vm_id;

    output  logic                      pap_sq_valid;
    output  logic [ISA_BITS+REG_WIDTH+1-1:0]   pap_sq_res;
    output  logic [3:0]                pap_sq_vm_id;
    input                              pap_sq_ready;
    output  logic                      pap_sq_hq_rel_valid;
    output  logic   [3:0]              pap_sq_hq_rel_vm_id;
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
        } = sq_pap_data;
    logic    src0_tmp [REG_WIDTH-1:0];
    logic    src1_tmp [REG_WIDTH-1:0];
    logic    src0_truncated_bit;
    logic    src1_truncated_bit;

wire    sync_push = sq_pap_valid && sq_pap_ready;
wire    sync_din  = opcode==3'h4;   // 1: MODMUL, 0: MODMUL_ACC
wire    sync_pop0;      
wire    sync_pop1;
wire    sync_dout0;         // used to control if modmul result is sent to acc
wire    sync_dout1;         // used to select result from modmul or acc
wire    sync_empty0;
wire    sync_empty1;
wire    sync_full;
wire    obuf_push;
wire    [4+ISA_BITS+REG_WIDTH+1-1:0]    obuf_din;
wire    obuf_pop;
wire    [4+ISA_BITS+REG_WIDTH+1-1:0]    obuf_dout;
wire    obuf_full;
wire    obuf_empty;

js_vm_sfifo_1w2r #(.WIDTH(1), .DEPTH(32)) u_sync_fifo (
    .clk        (clk),
    .rstn       (rstn),
    .push       (sync_push),
    .din        (sync_din),
    .pop0       (sync_pop0),
    .dout0      (sync_dout0),
    .pop1       (sync_pop1),
    .dout1      (sync_dout1),
    .empty0     (sync_empty0),
    .empty1     (sync_empty1),
    .full       (sync_full)
);

wire    lff_push;
wire    lff_pop;
wire    [4+ISA_BITS+REG_WIDTH+1-1:0]  lff_dout;
wire    lff_empty;
wire    lff_full;

    logic [DATA_WIDTH-1:0]             monmul_a;
    logic [DATA_WIDTH-1:0]             monmul_b;
    logic [DATA_WIDTH-1:0]             monmul_res;
    logic                              monmul_o_valid;
    logic                              monmul_o_ready;
    logic [ISA_BITS+1-1:0]             sq_pap_isa_dly [MODMUL_DELAY-1:0];
    logic [3:0]                        sq_pap_vm_id_dly[MODMUL_DELAY-1:0];
    logic                              acc_o_valid;
    logic                              acc_o_ready;
    logic [3:0]                        acc_o_vm_id;
    logic [ISA_BITS+REG_WIDTH+1-1:0]   acc_o_res;
//    assign pap_sq_valid = (!sync_empty1 && sync_dout1) ? !lff_empty : acc_o_valid;
//    assign pap_sq_res   = (!sync_empty1 && sync_dout1) ? lff_dout[ISA_BITS+REG_WIDTH+1-1:0] : acc_o_res;
//    assign pap_sq_vm_id = (!sync_empty1 && sync_dout1) ? lff_dout[4+ISA_BITS+REG_WIDTH+1-1:ISA_BITS+REG_WIDTH+1] : acc_o_vm_id;
//    assign acc_o_ready  = (!sync_empty1 && !sync_dout1) && pap_sq_ready;
wire    merge_o_valid = (!sync_empty1 && sync_dout1) ? !lff_empty : acc_o_valid;
wire    [ISA_BITS+REG_WIDTH+1-1:0]    merge_o_res = (!sync_empty1 && sync_dout1) ? lff_dout[ISA_BITS+REG_WIDTH+1-1:0] : acc_o_res;
wire    [3:0]   merge_o_vm_id = (!sync_empty1 && sync_dout1) ? lff_dout[4+ISA_BITS+REG_WIDTH+1-1:ISA_BITS+REG_WIDTH+1] : acc_o_vm_id;
wire    merge_o_ready = !obuf_full;
assign  acc_o_ready = (!sync_empty1 && !sync_dout1) && merge_o_ready;

assign obuf_push = merge_o_valid && merge_o_ready;
assign obuf_din  = {merge_o_vm_id, merge_o_res};
assign obuf_pop  = pap_sq_valid && pap_sq_ready;
assign {pap_sq_vm_id, pap_sq_res} = obuf_dout;
assign pap_sq_valid = !obuf_empty;
js_vm_sfifo #(.WIDTH(4+ISA_BITS+REG_WIDTH+1), .DEPTH(2)) obuf_fifo (
    .clk        (clk),
    .rstn       (rstn),
    .push       (obuf_push),
    .din        (obuf_din),
    .pop        (obuf_pop),
    .dout       (obuf_dout),
    .full       (obuf_full),
    .empty      (obuf_empty)
);





    assign sync_pop0 = monmul_o_valid && monmul_o_ready;
//    assign sync_pop1 = pap_sq_valid && pap_sq_ready;
    assign sync_pop1 = merge_o_valid && merge_o_ready;
//    assign lff_pop   = pap_sq_valid && pap_sq_ready && sync_dout1;
    assign lff_pop   = merge_o_valid && merge_o_ready && sync_dout1;
    //logic                              sq_pap_valid_dly[MODMUL_DELAY-1:0];                 
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
    assign src0_truncated_bit = src0_tmp[src0_imm];
    assign src1_truncated_bit = src1_tmp[src1_imm];    
    assign monmul_a = src0_fmt==4'ha ? {{(DATA_WIDTH-1){1'b0}}, src0_truncated_bit}: src0_value[DATA_WIDTH-1:0];
    assign monmul_b = src1_fmt==4'ha ? {{(DATA_WIDTH-1){1'b0}}, src1_truncated_bit}: src1_value[DATA_WIDTH-1:0];
    genvar dly;
    generate
        for (dly=0; dly<MODMUL_DELAY; dly=dly+1) begin: DELAY
            if (dly==0) begin
                always @ (posedge clk) begin
                    if (monmul_o_ready) begin
                        sq_pap_isa_dly[dly]  <= sq_pap_data[2*REG_WIDTH+:ISA_BITS+1];
                        sq_pap_vm_id_dly[dly]<= sq_pap_vm_id;
                        //sq_pap_valid_dly[dly]<= sq_pap_valid;
                    end
                end
            end
            else begin
                always @ (posedge clk) begin
                    if (monmul_o_ready) begin
                        sq_pap_isa_dly[dly] <= sq_pap_isa_dly[dly-1];
                        sq_pap_vm_id_dly[dly]<= sq_pap_vm_id_dly[dly-1];
                        //sq_pap_valid_dly[dly]<= sq_pap_valid_dly[dly-1];
                    end
                end
            end
        end
    endgenerate
    assign sq_pap_ready = monmul_o_ready && !sync_full;
    //assign sq_pap_ready = pap_sq_ready;
    //assign pap_sq_valid = sq_pap_valid_dly[MODMUL_DELAY-1];
    //assign pap_sq_res   = {sq_pap_isa_dly[MODMUL_DELAY-1],3'h6, 8'h0, monmul_res[DATA_WIDTH-1:0]};
    //assign pap_sq_vm_id = sq_pap_vm_id_dly[MODMUL_DELAY-1];

    wire    pap_res_valid = pap_sq_valid && pap_sq_ready;
    wire    [FC_NUM-1:0]    pap_sq_sf = get_sf(pap_sq_res[ISA_BITS+REG_WIDTH+1-1-:ISA_BITS]);
    wire    [FC_NUM-1:0]    pap_fc_dec = {FC_NUM{pap_res_valid}} & pap_sq_sf;
    wire    [3:0]    pap_res_vm_id = pap_sq_vm_id;
/*
    always @(posedge clk or negedge rstn)
    if(!rstn) begin
        pap_sq_hq_rel_valid <= 1'b0;
        pap_sq_fc_dec   <= 2'b00;
        pap_sq_fc_dec_vm_id <= 4'b0000;
    end else begin
        pap_sq_hq_rel_valid <= pap_res_valid;
        pap_sq_fc_dec   <= pap_fc_dec;
        pap_sq_fc_dec_vm_id <= pap_res_vm_id;
    end
*/
always @* begin
        pap_sq_hq_rel_valid = pap_res_valid;
        pap_sq_fc_dec   = pap_fc_dec;
        pap_sq_fc_dec_vm_id = pap_res_vm_id;
end
    assign pap_sq_hq_rel_vm_id = pap_sq_fc_dec_vm_id;

//    assign pap_sq_fc_dec_vm_id = sq_pap_vm_id_dly[MODMUL_DELAY-1];
//    assign pap_sq_hq_rel_vm_id = sq_pap_vm_id_dly[MODMUL_DELAY-1];
//    assign pap_sq_fc_dec       = sq_pap_isa_dly[MODMUL_DELAY-1][8+:2]|{2{pap_sq_valid}};
//    assign pap_sq_hq_rel_valid = pap_sq_valid;
    
    //monmul_single_256 #(.DATA_IN_WIDTH(256), .DATA_OUT_WIDTH(256)) u_monmul
    //   (
    //       .clk  (clk),
    //       .rst_n(rstn),
    //       .en   (pap_sq_ready),
    //       .a    (monmul_a),
    //       .b    (monmul_b),
    //       .prime(sq_pap_q),
    //       .mu   (sq_pap_mu),
    //       .res  (monmul_res) 
    //   );
    barr_modmult #(.DATA_WIDTH(DATA_WIDTH), .E_WIDTH(2), .VALID_WIDTH(1)) u_barr_modmul
        (   
            .clk    (clk),
            .rst_n  (rstn),
            .mul_a  (monmul_a),
            .mul_b  (monmul_b),
            .pre_c  (sq_pap_mu[DATA_WIDTH:0]),
            .prime  (sq_pap_q[DATA_WIDTH-1:0]),
            .en     (monmul_o_ready),
            .i_valid(sq_pap_valid),
            .o_valid(monmul_o_valid),
            .res    (monmul_res)
        );
    wire    modacc_i_valid = monmul_o_valid && !sync_empty0 && sync_dout0==1'b0;
    wire    modacc_i_ready;
    assign  monmul_o_ready = !lff_full && modacc_i_ready;
    js_vm_modacc u_modacc
        (
            .clk    (clk),
            .rstn   (rstn),
            .data   ({sq_pap_isa_dly[MODMUL_DELAY-1],3'h6, 8'h0, monmul_res[DATA_WIDTH-1:0]}),
            .q      (sq_pap_q[DATA_WIDTH-1:0]),
            .res    (acc_o_res),
            .i_vm_id(sq_pap_vm_id_dly[MODMUL_DELAY-1]),
            .o_vm_id(acc_o_vm_id),
//            .i_valid(monmul_o_valid),
            .i_valid(modacc_i_valid),
            .o_valid(acc_o_valid),
//            .i_ready(monmul_o_ready),
            .i_ready(modacc_i_ready),
            .o_ready(acc_o_ready)
        ); 

assign lff_push = !sync_empty0 && sync_dout0==1'b1 && !lff_full && monmul_o_valid;


js_vm_sfifo #(.WIDTH(4+ISA_BITS+REG_WIDTH+1), .DEPTH(10)) u_mmul_lff (
    .clk    (clk),
    .rstn   (rstn),
    .push   (lff_push),
    .din    ({sq_pap_vm_id_dly[MODMUL_DELAY-1], sq_pap_isa_dly[MODMUL_DELAY-1],3'h6, 8'h0, monmul_res[DATA_WIDTH-1:0]}),
    .pop    (lff_pop),
    .dout   (lff_dout),
    .empty  (lff_empty),
    .full   (lff_full)
);


assign pap_active = !lff_empty || !obuf_empty || !sync_empty0 || !sync_empty1 || sq_pap_valid ;

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

