module js_vm_mip_top
    (/*AUTOARG*/
   // Outputs
   mip_active, sq_mip_ready, mip_sq_fc_dec, mip_sq_fc_dec_vm_id,
   mip_sq_res, mip_sq_vm_id, mip_sq_valid,
   // Inputs
   clk, rstn, sq_mip_valid, sq_mip_data, sq_mip_q, sq_mip_vm_id,
   mip_sq_ready
   );
    `include "js_vm.vh"
    input clk;
    input rstn;
    output  mip_active;
    input sq_mip_valid;
    input [ISA_BITS+2*REG_WIDTH+1-1:0] sq_mip_data;
    input [255:0]                      sq_mip_q;
    input [3:0]                        sq_mip_vm_id;
    output                             sq_mip_ready;

    output  logic   [FC_NUM-1:0]              mip_sq_fc_dec;
    output  logic   [3:0]              mip_sq_fc_dec_vm_id;

    output[ISA_BITS+REG_WIDTH+1-1:0]   mip_sq_res;
    output  [3:0]                      mip_sq_vm_id;
    output                             mip_sq_valid;
    input                              mip_sq_ready;



    logic                              modinv_go;
    logic                              modinv_valid;
    logic [DATA_WIDTH-1:0]             modinv_a;//src0, the number needed to get its inverse
    logic [DATA_WIDTH-1:0]             modinv_R; //a's modular inverse
    logic [DATA_WIDTH-1:0]             modinv_b;//return src1 when src0 is zero
    logic [DATA_WIDTH-1:0]             modinv_b_r;//return src1 when src0 is zero
    logic                              modinv_a_is_zero;
    logic                              modinv_a_is_zero_r;
    logic [ISA_BITS+1:0]  sq_mip_isa_r;
    logic [3:0]           sq_mip_vm_id_r;
    logic busy;
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
        } = sq_mip_data;
    logic    src0_tmp [REG_WIDTH-1:0];
    logic    src1_tmp [REG_WIDTH-1:0];
    logic    src0_truncated_bit;
    logic    src1_truncated_bit;
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

    assign modinv_a = src0_fmt==4'ha ? {{(DATA_WIDTH-1){1'b0}}, src0_truncated_bit}: src0_value[DATA_WIDTH-1:0];
    assign modinv_b = src1_fmt==4'ha ? {{(DATA_WIDTH-1){1'b0}}, src1_truncated_bit}: src1_value[DATA_WIDTH-1:0];
    assign modinv_a_is_zero =  modinv_a == 0;

wire	sff_push;
wire	[5+ISA_BITS+1+DATA_WIDTH-1:0]	sff_din;
wire	sff_pop;
wire	[5+ISA_BITS+1+DATA_WIDTH-1:0]	sff_dout;
wire	sff_empty;
wire	sff_full;
assign sff_push = sq_mip_valid && sq_mip_ready;
assign sff_din  = {modinv_a_is_zero, sq_mip_vm_id, sq_mip_data[2*REG_WIDTH+:ISA_BITS+1], modinv_b};
assign sff_pop  = mip_sq_valid && mip_sq_ready;
js_vm_sfifo #(.WIDTH(5+ISA_BITS+1+DATA_WIDTH), .DEPTH(4)) u_sync_fifo (
	.clk		(clk),
	.rstn		(rstn),
	.push		(sff_push),
	.din		(sff_din),
	.pop		(sff_pop),
	.dout		(sff_dout),
	.full		(sff_full),
	.empty		(sff_empty)
);

wire	dff_push;
wire	[DATA_WIDTH-1:0]	dff_din;
wire	dff_pop;
wire	[DATA_WIDTH-1:0]	dff_dout;
wire	dff_empty;
wire	dff_full;
js_vm_sfifo #(.WIDTH(DATA_WIDTH), .DEPTH(2)) u_data_fifo (
	.clk		(clk),
	.rstn		(rstn),
	.push		(dff_push),
	.din		(dff_din),
	.pop		(dff_pop),
	.dout		(dff_dout),
	.full		(dff_full),
	.empty		(dff_empty)
);



wire	modi_valid = sq_mip_valid && !modinv_a_is_zero;
wire	modi_ready;
assign  modinv_go = modi_valid && modi_ready;
reg	[1:0]	modi_ot;
always @(posedge clk or negedge rstn)
if(!rstn)
    modi_ot <= 2'd2;
else
    modi_ot <= modi_ot - (modi_valid && modi_ready) + dff_pop;
assign modi_ready = !busy && modi_ot!=2'b0;
assign	sq_mip_ready = !sff_full && (modinv_a_is_zero ? 1'b1 : modi_ready);

assign dff_push = modinv_valid;
assign dff_din  = modinv_R;

wire	out_is_zero;
wire	[ISA_BITS-1:0]	out_isa;
wire	out_cc;
wire	[DATA_WIDTH-1:0] out_b;
assign {out_is_zero, mip_sq_vm_id, out_isa, out_cc, out_b} = sff_dout;

assign mip_sq_valid = !sff_empty && (out_is_zero ? 1'b1 : !dff_empty);
assign mip_sq_res   = (!sff_empty && out_is_zero) ? {out_isa, out_cc, {(REG_WIDTH-DATA_WIDTH){1'b0}}, out_b} : {out_isa, out_cc, {(REG_WIDTH-DATA_WIDTH){1'b0}}, dff_dout};

assign dff_pop = sff_pop && !out_is_zero;


wire    [FC_NUM-1:0]    mip_sq_sf = get_sf(out_isa);
    wire    [3:0]   fc_dec_vm_id = mip_sq_vm_id;
    wire    [FC_NUM-1:0]   fc_dec = mip_sq_sf & {FC_NUM{mip_sq_valid && mip_sq_ready}};
/*
    always @(posedge clk or negedge rstn)
    if(!rstn) begin
        mip_sq_fc_dec   <= 2'b00;
        mip_sq_fc_dec_vm_id <=4'b0;
    end else begin
        mip_sq_fc_dec   <= fc_dec;
        mip_sq_fc_dec_vm_id <= fc_dec_vm_id;
    end
*/
always @* begin
        mip_sq_fc_dec   = fc_dec;
        mip_sq_fc_dec_vm_id = fc_dec_vm_id;
end

    always @ (posedge clk or negedge rstn) begin
        if (!rstn)
            busy <= 0;
        else if (modinv_go) begin
            busy <= 1;
        end
        else if (modinv_valid) begin
            busy <= 0;
        end
        else begin
            busy <= busy;
        end
    end

    mod_inverse #(.MODULU_LENGTH(DATA_WIDTH)) u_modinv
    (
        .clk    (clk),
        .rstn   (rstn),
        .go     (modinv_go),
        .valid  (modinv_valid),
        .prime_q(sq_mip_q[DATA_WIDTH-1:0]),
        .a      (modinv_a),//the number needed to get its inverse
        .R      (modinv_R) //a's modular inverse
    );

assign mip_active = busy || !sff_empty || sq_mip_valid;

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
